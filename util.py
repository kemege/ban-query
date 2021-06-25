import os
import datetime
import git

def getBuildInfo(filename: str) -> dict:
    stat = os.stat(filename)
    fileTimestamp = stat.st_mtime
    fileDatetime = datetime.datetime.fromtimestamp(fileTimestamp)

    return {
        'artifact': filename,
        'name': filename,
        'version': fileDatetime.strftime('%Y-%m-%d'),
        'time': fileDatetime
    }

def getGitInfo(path: str = '.') -> dict:
    repo = git.Repo(path)
    branch = repo.active_branch.name
    [commit] = list(repo.iter_commits(branch, max_count=1))
    return {
        'commit': commit.message,
        'branch': branch,
        'time': commit.committed_datetime
    }