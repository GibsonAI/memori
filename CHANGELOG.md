# Changelog

All notable changes to the Memori Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Fixed multi-turn conversation ingestion for AzureOpenAI and OpenAI clients. Previously, only the first conversation turn was being recorded. Now `conversation_id` is resolved early in the request lifecycle, ensuring all conversation turns are properly ingested into the same conversation. (Fixes #83)

[3.0.0]: https://github.com/MemoriLabs/Memori/releases/tag/v3.0.0
