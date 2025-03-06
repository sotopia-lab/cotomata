from datasets import load_dataset
import json
import collections
from collections import Counter


ds = load_dataset("princeton-nlp/SWE-bench_Verified")

repos = set()
for dp in ds['test']:
    repos.add(dp['repo'])


statistic = {}
for repo in sorted(list(repos)):
    repo_owner, repo_name = repo.split('/')
    print(f"Analyzing {repo_owner}/{repo_name}")
    with open(f"pr_information/pr_information_{repo_owner}__{repo_name}.json", "r") as f:
        data = json.loads(f.read())
    
    stats = {}
    stats["Total PRs"] = 300
    stats["Merged PRs"] = len(data)
    files = []
    additions = []
    deletions = []
    changes = []
    file_names = Counter()
    file_prs = collections.defaultdict(list)
    for pr, pr_info in data.items():
        files.append(len(pr_info["files"]))
        additions.append(sum([f["additions"] for f in pr_info["files"]]))
        deletions.append(sum([f["deletions"] for f in pr_info["files"]]))
        changes.append(sum([f["changes"] for f in pr_info["files"]]))

        for file in pr_info["files"]:
            file_names[file["filename"]] += 1
            file_prs[file["filename"]].append(pr_info["pr"]["number"])
    
    top_10_files = file_names.most_common(10)
    top_10_files_with_prs = {filename: file_prs[filename] for filename, _ in top_10_files}

    stats["Average Modified Files"] = round(sum(files) / len(files), 2)
    stats["Average Added Lines"] = round(sum(additions) / len(additions), 2)
    stats["Average Deleted Lines"] = round(sum(deletions) / len(deletions), 2)
    stats["Average Changed Lines"] = round(sum(changes) / len(changes), 2)
    # stats["Top 10 Modified Files"] = top_10_files
    stats["Top 10 Modified Files with PR Numbers"] = top_10_files_with_prs

    statistic[f"{repo_owner}/{repo_name}"] = stats

with open("pr_information/pr_statistics.json", "w") as f:
    f.write(json.dumps(statistic, indent=4))


