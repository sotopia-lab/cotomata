import fs from 'fs';
import { execSync } from 'child_process';
import axios from 'axios';
import path from 'path';

/**
 * Utility to generate a timestamp string, e.g. "2025-01-08_14-00-52".
 */
function getTimestamp() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const hh = String(now.getHours()).padStart(2, '0');
  const min = String(now.getMinutes()).padStart(2, '0');
  const ss = String(now.getSeconds()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}_${hh}-${min}-${ss}`;
}

/**
 * Retrieve the current application-default GCP access token using gcloud CLI.
 */
function getAccessToken() {
  try {
    const token = execSync('gcloud auth application-default print-access-token', {
      encoding: 'utf-8',
    });
    return token.trim();
  } catch (error) {
    console.error('Error retrieving access token:', error.message);
    process.exit(1); // Exit if token retrieval fails
  }
}

/**
 * Reads the system instruction message from a file.
 */
function constructSystemMessage(systemMessageFilePath) {
  if (!fs.existsSync(systemMessageFilePath)) {
    console.error('Invalid system message file name!');
    process.exit(1);
  }
  return fs.readFileSync(systemMessageFilePath, { encoding: 'utf-8' }).trim();
}

/**
 * Reads the content of the given file and returns it as a user prompt.
 */
function buildPromptFromFile(filePath) {
  if (!fs.existsSync(filePath)) {
    console.error('Invalid file name!');
    process.exit(1);
  }

  const transcriptText = fs.readFileSync(filePath, { encoding: 'utf-8' }).trim();
  return (
    "Below is the interview transcript data. " +
    "Please evaluate the candidate according to the guidelines provided.\n\n" +
    transcriptText
  );
}

/**
 * Main logic to:
 * 1) Read transcript.
 * 2) Construct system/user messages.
 * 3) Call Vertex AI Anthropic model.
 * 4) Parse and store results in output JSON.
 */
async function main(
  inputFile,
  outputFile,
  projectId,
  location,
  systemMessageFilePath
) {
  // Check if the input file exists
  if (!fs.existsSync(inputFile)) {
    console.error('Invalid file name');
    process.exit(1);
  }

  // Prepare system message from file
  const systemMessage = constructSystemMessage(systemMessageFilePath);

  // Read transcript from local file
  const transcriptText = fs.readFileSync(inputFile, { encoding: 'utf-8' }).trim();

  // Build user prompt
  const userPrompt =
    "Below is the interview transcript data. " +
    "Please evaluate the candidate according to the guidelines provided.\n\n" +
    transcriptText;

  // Get access token
  const authToken = getAccessToken();

  // Model info
  const MODEL = 'claude-3-5-sonnet-v2@20241022';
  const anthropicVersion = 'vertex-2023-10-16';

  // The endpoint for the raw streaming predict method
  const endpoint = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/anthropic/models/${MODEL}:streamRawPredict`;

  // Construct the request body
  const requestBody = {
    anthropic_version: anthropicVersion,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: systemMessage + userPrompt,
          },
        ],
      },
    ],
    max_tokens: 1024,
    stream: false,
  };

  let responseContent = '';

  try {
    console.log('Sending request to Claude 3.5 Sonnet v2...\n');
    const response = await axios.post(endpoint, requestBody, {
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json; charset=utf-8',
      },
    });

    console.log("===== Model's Parsed Content =====");
    console.log(JSON.stringify(response.data.content, null, 2));

    // Extract content from Claude response
    const contentArray = response.data?.content;
    if (contentArray && contentArray.length > 0 && contentArray[0].type === 'text') {
      responseContent = contentArray[0].text;
    } else {
      responseContent = '';
    }

  } catch (error) {
    console.error('Error during API request:', error.response?.data || error.message);
    process.exit(1);
  }

  // Console log the raw content from Claude
  console.log("===== Model's Raw Output =====\n");
  console.log(responseContent);
  console.log("\n=============================\n");

  // Attempt to parse the JSON
  let parsedJson;
  try {
    parsedJson = JSON.parse(responseContent);
  } catch (err) {
    console.warn('Warning: Response was not valid JSON. Storing null for evaluation_scores.\n');
    parsedJson = { evaluation_scores: null };
  }

  // Combine interview data, raw response, and evaluation scores
  const outputData = {
    interview_data: transcriptText,
    assistant_raw_response: responseContent,
    evaluation_scores: parsedJson.evaluation_scores,
  };

  // Ensure the output directory exists
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });

  // Write final combined results to output JSON
  fs.writeFileSync(outputFile, JSON.stringify(outputData, null, 2), {
    encoding: 'utf-8',
  });

  console.log(`Evaluation complete. Results saved to '${outputFile}'\n`);
  console.log('Parsed evaluation_scores (if available):');
  console.log(outputData.evaluation_scores);
}

// Generate a timestamped output file name
const inputFilePath = process.argv[2];
const systemMessageFilePath = process.argv[3];
const timestamp = getTimestamp();
const outputFilePath = `results/evaluation_output_${timestamp}.json`;

// Project details
const PROJECT_ID = 'gcp-multi-agent';
const LOCATION = 'us-east5';

main(inputFilePath, outputFilePath, PROJECT_ID, LOCATION, systemMessageFilePath);