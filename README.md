# Rodhaj

[![CodeQL](https://github.com/transprogrammer/rodhaj/actions/workflows/codeql.yml/badge.svg)](https://github.com/transprogrammer/rodhaj/actions/workflows/codeql.yml) [![Lint](https://github.com/transprogrammer/rodhaj/actions/workflows/lint.yml/badge.svg)](https://github.com/transprogrammer/rodhaj/actions/workflows/lint.yml) [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=transprogrammer_rodhaj&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=transprogrammer_rodhaj) [![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=transprogrammer_rodhaj&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=transprogrammer_rodhaj)

A improved, modern version of ModMail for Transprogrammer

> [!IMPORTANT]
> We would prefer if you do not run instances of Rodhaj (included self-hosted ones). The source code is provided as-is and is for educational and development purposes only.

## What is Rodhaj?

Just like ModMail, Rodhaj serves to be the transprogrammer's official ModMail bot. By creating a shared inbox, it allows for users and staff to seamlessly communicate safely, securely, and privately.

Unlike ModMail, this bot is fine-tuned for the needs of the transprogrammer community. As a result, **there is no public invite**.

## How does it work?

The process is extremely similar to ModMail, but with major differences. When a member
sends a direct message to the bot, Rodhaj will create a new ticket (which is a forum post)
internally for staff to view. From there, each ticket is tied with a member and DMs from Rodhaj will be processed and sent to their respective tickets.

Staff are free to swap and work on multiple tickets as needed. Once a ticket is closed, the staff will be automatically unassigned from the ticket, and a new DM to Rodhaj will prompt the user to create a new ticket. In short, it's designed to be a replacement to ModMail.

## Contributing

Contributions to Rodhaj are always welcomed. These could be as small as
changing documentation to adding new features. If you are interested to start
the process, please consult the [contributing guidelines](.github/CONTRIBUTING.md) before
you get started.
