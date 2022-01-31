# How To Contribute to Routerling!!!

Thank you so much for considering to use the most valuable resource in the universe - your time to help move open source forward through **Routerling**.

## Support Questions
Please don't use the issue tracker for this. The issue tracker is a tool to address bugs and feature request in Routerling itself. Use any of the following
resources for questions about Routerling or issues with your own code:

- The mailing list routerling@python.org for long term discussions or larger issues.
- Ask on [Stack Overflow](https://www.stackoverflow.com). Search with Google or Bing using: site:stackoverflow.com routerling {search term, exception message etc.}
- Ask via [GitHub Discussions](https://www.github.com/rayattack/routerling/discussions)


##  Reporting Issues
Include the following information in your ticket:

- What you expected to happen
- What happened instead
- Where possible [A Small Reference Example](https://stackoverflow.com/help/minimal-reproducible-example) to help troubleshoot the issue and or ease the process of ensuring the problem is not from your code.
- List your Python and Routerling versions. Where possible, check if the issue has already been fixed in newer code/releases in the repository/pypi.

## Submitting Patches
If you could not find an already open issue for what you want to submit, please open one for discussion before working on a PR. You can work on any issue that does not have an open PR linked to it, or a maintainer assigned to it.
These show up in the sidebar.
No need to ask if you can work on an issue that interests you.

Kindly include the following in your patch:

- Use Black to format your code. This and other tools will run automatically if you install pre-commit using the instructions below.
- Include tests if your patch adds or changes code. Make sure the test fails without your patch.
- Update any relevant docs pages and docstrings. Docs pages and docstrings should be wrapped at 72 characters.
- Add an entry in [CHANGES](changes.md). Use the same style as other entries. Also include .. versionchanged:: inline changelogs in relevant docstrings.
