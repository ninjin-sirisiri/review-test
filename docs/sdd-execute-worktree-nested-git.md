# Linked worktree と Recorder の nested git 拒否

日付: 2026-08-31

sdd-execute で isolated git worktree（`.worktrees/timeline-ui`）を作ったあと、`.worktrees/timeline-ui/.sdd/progress.md` へ判断記録しようとすると Recorder が次を返す。

- code: `REPOSITORY_NOT_REGISTERED`
- message: `target is inside an unregistered nested repository`

原因は linked worktree の `.git` ファイルを、親リポジトリ配下の未登録 nested repository として `rejectNestedRepository` が見ること。親セッションの `repositoryRoot` のままでは permit を出せない。Cursor の hook は `AI_REVIEW_REPOSITORY_ROOT` が親ワークスペース固定のため、worktree を別 root として記録しても gate 側の root と一致しない。

このセッションでは worktree を残したまま、実装は元の checkout で続行した。
