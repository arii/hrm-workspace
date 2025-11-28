WORKSPACE=/home/ari/workspace

alias remove_worktrees="rm -rf ${WORKSPACE}/worktrees/* && git -C ${WORKSPACE}/leader worktree prune"

start_worktree(){
    cp ${WORKSPACE}/leader/.env.production ${WORKSPACE}/worktrees/${1}
    sh ${WORKSPACE}/worktrees/${1}/start-production.sh
}

alias pr_draft_numbers="gh pr list --state open --draft --repo arii/hrm  --json number --jq '.[].number'"
