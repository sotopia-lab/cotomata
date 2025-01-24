# Evaluation Set-up Guide

## Set-up
Make sure you are in the 'evaluation' directory:
```
cd evaluation
```
Run the following command to install required libraries. (Make sure you have Node.js installed)
```
npm install
```

## Running the Script
Run the following command to run the evaluation script. The first argument should be the file path to your input data. You may also need to log into GCP. 
```
node index.js <input-file-path>
```
For example:
```
node index.js sample_data/interview_openhands_2025-01-08_14-00-52.jsonl
```
Results will output to the 'results' folder with the timestamped file name printed in your terminal. 

## Error Messages for Claude

If you see the following error after you run the script, try re-running.
```
Error during API request: {
  type: 'error',
  error: { type: 'overloaded_error', message: 'Overloaded' }
}
```


