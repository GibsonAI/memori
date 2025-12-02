[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Infrastructure

We are committed to making sure you have the infrastructure you need to run Memori anywhere with as little effort as possible.  This includes partnering with infrastructure providers to integrate systems and tools into Memori.

This document will maintain a list of our partners and what we've done to integrate. You don't need to work with any of the technology here but if you find something useful or easy to use we want to make sure we support you.

If you would like to see us integrate something please reach out and let us know!

## CockroachDB

**Memori + CockroachDB** brings durable, distributed memory to AI - instantly, globally, and at any scale. Memori transforms conversations into structured, queryable intelligence, while CockroachDB keeps that memory available, resilient, and consistently accurate across regions. Deploy and scale effortlessly from prototype to production with zero downtime on enterprise-grade infrastructure. Give your AI a foundation to remember, reason, and evolve - with the simplicity of cloud and the reliability and power of distributed SQL.

### How Does It Work?

Manage CockroachDB clusters by using [Memori's Command Line Interface (CLI)](https://github.com/MemoriLabs/Memori/blob/main/docs/CommandLineInterface.md).

#### Start a CockroachDB Cluster

```bash
python -m memori cockroachdb cluster start
```

This will provision and launch serverless, cloud infrastructure, build the Memori schema and provide you with the connection string you need to access the database.

#### Claim a CockroachDB Cluster

```bash
python -m memori cockroachdb cluster claim
```

You have 7 days to claim your CockroachDB cluster or it will be automatically deleted. Claiming is easy and only requires an email address.

#### Delete a CockroachDB Cluster

```bash
python -m memori cockroachdb cluster delete
```

Deletes your CockroachDB cluster including all of its data.
