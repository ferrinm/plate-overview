# The JSON sidecar records a basename, never a path

The sidecar records `source_name`, and the package strips every directory
component from it before it writes the file. The renderer applies the rule. It
does not trust the adapter to apply it.

The code this package was extracted from recorded the absolute experiment path.
That path is the most quotable line in a diagnostic artifact: a sidecar is small,
so it gets pasted whole into an issue or a message. An absolute path reconstructs
a share layout, a project directory and often an operator name, none of which the
reader of a QC figure needs.

A basename keeps the sidecar useful. It answers "which acquisition produced this
figure" for anyone who can already reach the acquisition, and it says nothing to
anyone who cannot.

The rule also binds the surrounding documentation. Do not annotate a quoted
sidecar with the directory it was found in. That undoes the rule in the one place
the rule exists to protect.
