
from interact_with_neo4j import iter_repos

for repo in iter_repos():
    print(repo.repository, repo.branch)