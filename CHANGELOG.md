# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of DevContainer Tools
- Simplified CLI interface for devcontainer management
- Automatic configuration merging between common and project settings
- Support for forwardPorts to appPort conversion
- Rich console output with colors and formatting
- Docker exec direct execution for improved performance
- Comprehensive test coverage
- GitHub Actions workflows for CI/CD

### Features
- `dev up` - Start or create development containers
- `dev exec` - Execute commands in running containers
- `dev status` - Show container status and configuration
- `dev rebuild` - Clean rebuild containers from scratch
- `dev init` - Initialize common configuration templates

## [0.0.1] - 2024-12-26

### Added
- Initial development release
- Core functionality for DevContainer management
- Configuration merging system
- Command-line interface with click
- Rich console output
- Comprehensive documentation
- Test suite with pytest
- CI/CD pipeline with GitHub Actions

### Dependencies
- click >= 8.1.0
- rich >= 13.0.0
- Python >= 3.8

### Breaking Changes
- None (initial release)

### Migration Guide
- This is the initial release, no migration needed

### Known Issues
- None reported

### Security
- No security issues identified in this release