# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues on
`ferrinm/plate-overview`. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run
inside a clone.

## Before you publish: this repository is public

The upstream acquisitions are not public, and an issue body is the easiest
place to leak one. So:

- **No real acquisition data in an issue** — no plate identifiers, no
  operator-bearing paths, no source filenames, in the title, the body or an
  attachment. Synthesise an example instead.
- **Quote sidecars verbatim.** The JSON sidecar records a basename, never an
  absolute path. Don't helpfully annotate it with the directory you found it
  in — that reconstructs the filesystem layout the basename rule exists to
  hide.

These are the repo's two house rules from `README.md`; they bind agent output
the same way they bind a human contributor's.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
