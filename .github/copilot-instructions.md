# Komodo Home Assistant Integration

A Home Assistant custom integration for monitoring [Komodo](https://github.com/mbecker20/komodo) infrastructure. This integration allows monitoring Komodo-managed servers, Docker stacks, and alerts directly from Home Assistant.

**ALWAYS follow these instructions first and fallback to search or bash commands only when you encounter unexpected information that contradicts the info here.**

## Working Effectively

### Environment Setup
- Install Python 3.12+ environment:
  - `python3 --version` - verify Python 3.12+
  - `pip3 install homeassistant` - NEVER CANCEL: takes 5-8 minutes. Set timeout to 15+ minutes.
  - `pip3 install komodo-api==1.18.4` - install required dependency (~30 seconds)

### Validation and Testing
- **NEVER CANCEL any validation commands** - they complete quickly but are critical
- Run basic validation (completes in <30 seconds):
  ```bash
  python3 -c "
  import sys
  sys.path.insert(0, 'custom_components')
  import komodo
  import komodo.const
  import komodo.config_flow
  print('Integration imports: OK')
  "
  ```
- Run integration-specific tests:
  - `python3 -m py_compile custom_components/komodo/*.py` - syntax validation (<5 seconds)
  - `python3 -m py_compile custom_components/komodo/sensors/*.py` - sensor validation (<5 seconds)

### Code Quality and Linting 
- **ALWAYS run these before committing** - CI will fail without them:
  - `pip3 install flake8 black isort mypy` - install linting tools (2-3 minutes)
  - `flake8 custom_components/komodo --max-line-length=88 --extend-ignore=E203` - style checking (<1 second)
  - `black --check custom_components/` - formatting validation (<1 second)
  - `isort --check-only custom_components/` - import sorting (<1 second) 
  - `mypy custom_components/komodo --ignore-missing-imports` - type checking (~25 seconds)

### Comprehensive Validation Script
- **ALWAYS run complete validation** before committing major changes:
- Create validation script in `/tmp/validate_integration.py`:
  ```python
  #!/usr/bin/env python3
  import subprocess, time
  def test_cmd(desc, cmd):
      start = time.time()
      result = subprocess.run(cmd, shell=True, cwd=".", capture_output=True)
      elapsed = time.time() - start
      status = "✓ PASS" if result.returncode == 0 else "✗ FAIL"
      print(f"{status} {desc} ({elapsed:.2f}s)")
      return result.returncode == 0
  
  tests = [
      ("Import test", 'python3 -c "import sys; sys.path.insert(0, \\"custom_components\\"); import komodo"'),
      ("Syntax check", "python3 -m py_compile custom_components/komodo/*.py"),
      ("Config flow", 'python3 -c "import sys; sys.path.insert(0, \\"custom_components\\"); from komodo.config_flow import ConfigFlow; ConfigFlow()"'),
  ]
  
  results = [test_cmd(desc, cmd) for desc, cmd in tests]
  print(f"Results: {sum(results)}/{len(results)} passed")
  ```
- Run with: `python3 /tmp/validate_integration.py` (takes ~3-5 seconds)
- The GitHub Actions CI runs two validations that **you cannot run locally**:
  - **HACS validation**: Validates integration meets HACS standards
  - **hassfest validation**: Home Assistant's official integration validator
- These run automatically on push/PR and take ~2-3 minutes each
- **NEVER try to bypass or duplicate CI locally** - the official tools require Docker environments you don't have access to

## Manual Testing and Validation

### Integration Loading Test
- **ALWAYS test integration loading after code changes**:
  - Run the basic import test above
  - Verify manifest.json is valid: `python3 -c "import json; print(json.load(open('custom_components/komodo/manifest.json')))"`

### Home Assistant Integration Test
- **You CANNOT run a full Home Assistant instance** in this environment
- **You CANNOT connect to a real Komodo instance** for testing
- **DO run import validation** to ensure integration would load correctly
- **DO test** that config flow, coordinator, and sensor classes can be instantiated

### Validation Scenarios
After making changes to the integration code, **ALWAYS**:
1. **Run basic syntax validation** - verify Python files compile
2. **Run import tests** - ensure all modules import correctly  
3. **Run linting tools** - fix style issues that will cause CI failure
4. **Verify manifest.json** - ensure version and dependencies are correct
5. **Test specific scenarios** (all include sys.path setup):
   - Server sensor changes: `python3 -c "import sys; sys.path.insert(0, 'custom_components'); from komodo.sensors.server import create_server_sensors"`
   - Stack sensor changes: `python3 -c "import sys; sys.path.insert(0, 'custom_components'); from komodo.sensors.stack import create_stack_sensors"` 
   - Config flow changes: `python3 -c "import sys; sys.path.insert(0, 'custom_components'); from komodo.config_flow import ConfigFlow; ConfigFlow()"`
   - Coordinator changes: `python3 -c "import sys; sys.path.insert(0, 'custom_components'); from komodo.coordinator import KomodoCoordinator"`

## Repository Structure and Key Files

### Core Integration Files
```
custom_components/komodo/
├── __init__.py           - Integration setup and teardown
├── manifest.json         - Integration metadata and dependencies  
├── const.py             - Constants and configuration keys
├── config_flow.py       - Configuration flow for HA UI setup
├── coordinator.py       - Data coordinator for API communication
├── base.py              - Base API client wrapper
├── sensor.py            - Sensor platform entry point  
├── update.py            - Update platform for container updates
├── sensors/             - Individual sensor implementations
│   ├── server.py        - Server state sensors
│   ├── stack.py         - Docker stack state sensors  
│   ├── alert.py         - Alert monitoring sensors
│   ├── common.py        - Shared sensor base classes
│   └── util.py          - Utility functions
├── strings.json         - UI strings for configuration
└── translations/        - Localized strings
    ├── en.json
    └── de.json
```

### Key Configuration Files
- **manifest.json**: Contains version (0.0.3), dependencies (komodo-api==1.18.4), and integration metadata
- **const.py**: Defines DOMAIN="komodo" and configuration constants
- **.github/workflows/**: CI pipeline with HACS and hassfest validation

## Common Development Tasks

### Adding New Sensor Types
1. Create sensor class in `sensors/` directory inheriting from `KomodoEntity`
2. Register in `sensor.py` async_setup_entry function
3. Add to coordinator data fetching in `coordinator.py`
4. **ALWAYS test**: import the new sensor class and instantiate it
5. **ALWAYS run**: full validation suite before committing

### Modifying API Communication  
1. Changes go in `coordinator.py` (data fetching) or `base.py` (API client)
2. **CRITICAL**: Ensure komodo-api version compatibility in manifest.json
3. **ALWAYS test**: API client instantiation and coordinator setup
4. **Consider**: Mock testing since you cannot connect to real Komodo instance

### Configuration Changes
1. Update `config_flow.py` for new configuration options
2. Add new constants to `const.py` 
3. Update `strings.json` and translation files if adding UI elements
4. **ALWAYS test**: `ConfigFlow()` instantiation after changes

## Timing and Performance

### Timing and Performance

### Validation Command Timing (measured):
- **Python compilation**: <5 seconds per directory
- **Import testing**: ~1.6 seconds per test
- **flake8 linting**: <0.2 seconds (finds 138+ existing issues)
- **black formatting**: <0.4 seconds  
- **isort import sorting**: <0.2 seconds
- **mypy type checking**: ~1.6 seconds (finds type issues, non-critical)
- **Full validation suite**: ~10-12 seconds total

### CI Pipeline Timing:
- **HACS validation**: ~2-3 minutes
- **hassfest validation**: ~2-3 minutes  
- **Total CI time**: ~5-7 minutes

### Development Workflow Timing:
- **Quick validation cycle**: <2 seconds (syntax + imports)
- **Full validation cycle**: ~10-12 seconds (includes all linting)
- **CI feedback loop**: 5-7 minutes after push

## Troubleshooting

### Import Errors
- **Always check**: `sys.path.insert(0, 'custom_components')` in test scripts
- **Verify**: komodo-api dependency is installed (`pip3 list | grep komodo-api`)
- **Common issue**: pydantic warnings are normal and can be ignored

### Linting Failures  
- **Style issues are common** - this codebase has 138+ flake8 issues
- **Focus on new issues** your changes introduce, not existing ones
- **Use --exclude** to ignore files you didn't modify: `flake8 --exclude=existing_file.py`

### CI Failures
- **HACS failures**: Usually manifest.json or repository structure issues
- **hassfest failures**: Integration metadata or Home Assistant compatibility  
- **Cannot reproduce locally** - these tools require specific Docker environments

### Testing Limitations
- **No real Komodo instance access** - use mock testing approaches
- **No full Home Assistant instance** - test individual components only  
- **No UI testing** - focus on backend integration code
- **No network requests** - mock API responses in tests

## Dependencies and Versions

### Required Dependencies (from manifest.json):
- **komodo-api==1.18.4** - Komodo API client library
- **Home Assistant Core** - Platform framework (auto-installed)

### Development Dependencies:
- **flake8** - Code style checking
- **black** - Code formatting  
- **isort** - Import sorting
- **mypy** - Type checking

### Version Information:
- **Current version**: 0.0.3 (in manifest.json)  
- **Home Assistant compatibility**: Modern versions (2024+)
- **Python requirement**: 3.12+

**CRITICAL REMINDERS:**
- **NEVER CANCEL validation commands** - they complete in under 1 minute
- **ALWAYS run linting** before committing - CI will fail without it
- **CANNOT test against real Komodo** - use import/instantiation testing
- **CANNOT run full Home Assistant** - test individual components only
- **Time budget**: Plan 5-10 minutes for full validation cycle per change