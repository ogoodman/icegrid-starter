Repository organisation
=======================

This repository is organised as a `base` branch containing useful
infrastructure for setting up an IceGrid development project, and a
number of other branches containing such projects.

Infrastructure changes which may be useful to all projects are
made in the `base` branch and merged with each project. 

In order to turn a fresh branch from `base` into a working project it
is necessary (at a minimum) to add `application.yml`,
`pillar/platform/dev.sls` and `pillar/platform/local.sls`.

Ideally the base branch would have been a completely independent
project, but it is in the nature of `Makefiles` and `Vagrantfiles`
that they need to live in the project directory. It could have been
developed as a code generator but that would make it harder to merge
infrastructure improvements into projects.
