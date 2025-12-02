[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Introduction to Command Line Interface (CLI)

The CLI allows you to manage your integration with Memori and perform actions such as starting a new database cluster, checking your quota or setting up your environment to run Memori.

## How Does It Work

To use the Memori CLI, execute the following from the command line:

```bash
python -m memori
```

This will display a menu of the available options. To execute a particular command, just provide the option and any params:

```bash
python -m memori <option> [params]
```

The menu provides a column indicating if a particular option requires additional parameters.

## CockroachDB

```bash
usage: python -m memori cockroachdb cluster <start | claim | delete>
```

Parameters:
- start: starts a new CockroachDB cluster
- claim: provides the URL for claiming the CockroachDB cluster
- delete: permanently removes the CockroachDB cluster including all of its data

If you do not have database infrastructure or want to provision serverless, cloud infrastructure you can execute these commands to manage a CockroachDB cluster. Executing the commands will provide output about the steps being taken, how to use the cluster with Memori and display your connection string.

## Quota

```bash
usage: python -m memori quota
```

Displays your available quota.

## Set Up

```bash
usage: python -m memori setup
```

Executes any necessary set up steps to prepare your environment for using Memori. Note, executing this command is not necessary but will cache any data you need to make sure real time execution of Memori is faster.

## Sign Up

```bash
usage: python -m memori sign-up <email_address>
```

Provides a convenience for signing up for a Memori API key.
