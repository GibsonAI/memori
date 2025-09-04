#!/usr/bin/env python3
"""
Enhanced documentation generation script for Memori SDK
Extracts from auto-docs-generation.yml workflow for better maintainability
"""

import os
import sys
import json
import yaml
import time
import traceback
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import tempfile
import shutil

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration class with environment-based settings"""
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    retry_delay_base: int = int(os.getenv('RETRY_DELAY_BASE', '2'))
    api_timeout: int = int(os.getenv('API_TIMEOUT', '300'))
    rate_limit_delay: int = int(os.getenv('RATE_LIMIT_DELAY', '1'))
    batch_size: int = int(os.getenv('BATCH_SIZE', '5'))
    max_concurrent: int = int(os.getenv('MAX_CONCURRENT', '3'))
    max_sample_docs: int = int(os.getenv('MAX_SAMPLE_DOCS', '3'))
    max_tokens: int = int(os.getenv('MAX_TOKENS', '8000'))
    temperature: float = float(os.getenv('TEMPERATURE', '0.1'))

config = Config()

class DocumentationError(Exception):
    """Custom exception for documentation generation errors"""
    pass

class RateLimitError(Exception):
    """Custom exception for rate limiting errors"""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_api_key(api_key: str) -> bool:
    """Validate Anthropic API key format"""
    try:
        if not api_key or len(api_key) < 10:
            return False
        return api_key.startswith('sk-ant-')
    except Exception:
        return False

def exponential_backoff(attempt: int, base_delay: int = 2) -> float:
    """Calculate exponential backoff delay"""
    return min(base_delay ** attempt, 60)  # Cap at 60 seconds

def safe_file_operation(operation, *args, **kwargs):
    """Wrapper for safe file operations with error handling"""
    try:
        return operation(*args, **kwargs), None
    except Exception as e:
        logger.error(f"File operation failed: {e}")
        return None, str(e)

def read_file_content(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Read file content safely with comprehensive error handling"""
    try:
        path = Path(file_path)
        if not path.exists():
            return None, f"File does not exist: {file_path}"
        
        if not path.is_file():
            return None, f"Path is not a file: {file_path}"
        
        # Check file size (limit to 1MB)
        if path.stat().st_size > 1024 * 1024:
            return None, f"File too large (>1MB): {file_path}"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            return None, f"File is empty: {file_path}"
        
        return content, None
        
    except UnicodeDecodeError:
        return None, f"File encoding error (not UTF-8): {file_path}"
    except PermissionError:
        return None, f"Permission denied: {file_path}"
    except Exception as e:
        return None, f"Unexpected error reading {file_path}: {str(e)}"

def write_file_content(file_path: str, content: str) -> Tuple[bool, Optional[str]]:
    """Write file content safely with atomic operations"""
    try:
        path = Path(file_path)
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first (atomic operation)
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8', 
            dir=path.parent, 
            delete=False
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Move temporary file to final location
        shutil.move(tmp_path, path)
        
        logger.info(f"Successfully wrote file: {file_path}")
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to write {file_path}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_framework_name(file_path: str) -> str:
    """Extract framework name from file path with validation"""
    try:
        path = Path(file_path)
        
        if 'integrations/' in file_path:
            filename = path.stem
            # Remove common suffixes
            for suffix in ['_example', '_integration', '_demo']:
                filename = filename.replace(suffix, '')
            return filename.lower()
        else:
            # For non-integration examples
            filename = path.stem
            return filename.replace('_', '-').lower()
    except Exception as e:
        logger.warning(f"Error extracting framework name from {file_path}: {e}")
        return 'unknown'

def get_existing_docs() -> Dict[str, str]:
    """Get existing documentation patterns with error handling"""
    existing_docs = {}
    docs_dir = Path('docs/examples')
    
    if not docs_dir.exists():
        logger.warning("docs/examples directory does not exist")
        return existing_docs
    
    try:
        for doc_file in docs_dir.glob('*.md'):
            content, error = read_file_content(doc_file)
            if content and not error:
                existing_docs[doc_file.name] = content
            elif error:
                logger.warning(f"Skipping {doc_file}: {error}")
        
        logger.info(f"Loaded {len(existing_docs)} existing documentation files")
        return existing_docs
        
    except Exception as e:
        logger.error(f"Error loading existing docs: {e}")
        return existing_docs

def create_claude_client(api_key: str):
    """Create Anthropic client with validation"""
    try:
        if not validate_api_key(api_key):
            raise ValidationError("Invalid API key format")
        
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        return client, None
        
    except ImportError:
        return None, "Anthropic library not installed"
    except Exception as e:
        return None, f"Failed to create Claude client: {str(e)}"

def create_documentation_with_retry(
    client, 
    example_file: str, 
    existing_docs: Dict[str, str]
) -> Tuple[Optional[str], Optional[str]]:
    """Generate documentation with retry logic and rate limiting"""
    
    for attempt in range(config.max_retries):
        try:
            logger.info(f"Generating documentation for {example_file} (attempt {attempt + 1})")
            
            # Read the example file
            example_content, error = read_file_content(example_file)
            if not example_content or error:
                return None, f"Failed to read example file: {error}"
            
            framework_name = get_framework_name(example_file)
            
            # Prepare sample documentation (limited by config)
            sample_docs = ""
            if existing_docs:
                sample_count = 0
                for doc_name, doc_content in list(existing_docs.items())[:config.max_sample_docs]:
                    # Truncate content to prevent token limit issues
                    truncated_content = doc_content[:3000]
                    sample_docs += f"\n\n--- Sample Documentation ({doc_name}) ---\n{truncated_content}...\n"
                    sample_count += 1
            
            # Prepare prompts
            system_prompt = """You are a code-reciprocator agent specialized in creating consistent, high-quality documentation following established patterns and architectural DNA.

Core responsibilities:
1. Analyze existing documentation patterns for structure and style consistency
2. Extract and replicate formatting, tone, and organizational approaches
3. Create new documentation that seamlessly integrates with existing patterns
4. Maintain architectural DNA across all integration documentation
5. Ensure professional quality and technical accuracy

Required documentation sections:
- Overview with clear integration benefits
- Complete code example with explanations  
- Step-by-step "What Happens" breakdown
- Expected output with realistic examples
- Database contents and schema information
- Setup instructions with prerequisites
- Use cases and practical applications
- Best practices and optimization tips
- Next steps and related resources

Quality standards:
- Use identical markdown structure as samples
- Maintain consistent professional tone
- Include framework-specific integration details
- Provide complete, working code examples
- Ensure technical accuracy and clarity"""

            user_prompt = f"""Create comprehensive documentation for this integration example following the exact patterns from existing documentation.

INTEGRATION FILE: {example_file}
FRAMEWORK: {framework_name}

EXAMPLE CODE:
```python
{example_content}
```

EXISTING DOCUMENTATION PATTERNS:
{sample_docs}

Requirements:
1. Follow EXACT same markdown structure and formatting
2. Use identical section organization and headers  
3. Maintain consistent professional tone and style
4. Include all standard sections with framework-specific content
5. Provide complete working examples with detailed explanations
6. Ensure integration benefits are clearly highlighted
7. Follow established architectural DNA patterns

Generate production-ready documentation for: docs/examples/{framework_name}-integration.md"""
            
            # Make API call with timeout
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=config.api_timeout
            )
            
            if response and response.content:
                content = response.content[0].text
                logger.info(f"Successfully generated documentation for {example_file}")
                
                # Rate limiting delay
                time.sleep(config.rate_limit_delay)
                
                return content, None
            else:
                raise DocumentationError("Empty response from Claude API")
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {example_file}: {error_msg}")
            
            # Check for rate limiting
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                if attempt < config.max_retries - 1:
                    delay = exponential_backoff(attempt + 1, config.retry_delay_base * 2)
                    logger.info(f"Rate limited, waiting {delay}s before retry...")
                    time.sleep(delay)
                    continue
                else:
                    return None, "Rate limit exceeded after all retries"
            
            # General retry logic
            if attempt < config.max_retries - 1:
                delay = exponential_backoff(attempt, config.retry_delay_base)
                logger.info(f"Waiting {delay}s before retry...")
                time.sleep(delay)
            else:
                return None, f"Failed after {config.max_retries} attempts: {error_msg}"
    
    return None, "Maximum retries exceeded"

def update_mkdocs_nav_safe(new_docs: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """Update mkdocs.yml navigation with comprehensive error handling and rollback"""
    mkdocs_path = 'mkdocs.yml'
    backup_path = f'{mkdocs_path}.backup'
    
    try:
        # Create backup first
        if Path(mkdocs_path).exists():
            shutil.copy2(mkdocs_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Read current config with full YAML support for Python object references
        with open(mkdocs_path, 'r', encoding='utf-8') as f:
            mkdocs_config = yaml.load(f, Loader=yaml.FullLoader)
        
        if not mkdocs_config or 'nav' not in mkdocs_config:
            return False, "Invalid mkdocs.yml structure"
        
        # Find Examples section
        nav = mkdocs_config.get('nav', [])
        examples_section = None
        examples_index = -1
        
        for i, section in enumerate(nav):
            if isinstance(section, dict) and 'Examples' in section:
                examples_section = section['Examples']
                examples_index = i
                break
        
        if examples_section is None:
            # Create Examples section if it doesn't exist
            examples_section = []
            nav.append({'Examples': examples_section})
            logger.info("Created new Examples section in navigation")
        
        # Add new documentation entries
        added_count = 0
        for framework_name in new_docs:
            doc_path = f"examples/{framework_name}-integration.md"
            display_name = f"{framework_name.title().replace('-', ' ')} Integration"
            
            # Check if entry already exists
            entry_exists = False
            for item in examples_section:
                if isinstance(item, dict):
                    if doc_path in item.values() or display_name in item.keys():
                        entry_exists = True
                        break
            
            if not entry_exists:
                examples_section.append({display_name: doc_path})
                logger.info(f"Added {display_name} to navigation")
                added_count += 1
            else:
                logger.info(f"Entry already exists: {display_name}")
        
        if added_count == 0:
            logger.info("No new navigation entries needed")
            return True, None
        
        # Write updated config with atomic operation using full dumper to preserve Python references
        success, error = write_file_content(mkdocs_path, yaml.dump(
            mkdocs_config, 
            default_flow_style=False, 
            sort_keys=False,
            allow_unicode=True,
            Dumper=yaml.Dumper
        ))
        
        if success:
            logger.info(f"Updated mkdocs.yml with {added_count} new entries")
            # Remove backup on success
            Path(backup_path).unlink(missing_ok=True)
            return True, None
        else:
            # Restore backup on failure
            if Path(backup_path).exists():
                shutil.move(backup_path, mkdocs_path)
                logger.warning("Restored mkdocs.yml from backup")
            return False, error
        
    except Exception as e:
        error_msg = f"Error updating mkdocs.yml: {str(e)}"
        logger.error(error_msg)
        
        # Restore backup on exception
        try:
            if Path(backup_path).exists():
                shutil.move(backup_path, mkdocs_path)
                logger.warning("Restored mkdocs.yml from backup after exception")
        except Exception as backup_error:
            logger.error(f"Failed to restore backup: {backup_error}")
        
        return False, error_msg

def process_files_in_batches(changed_files: List[str], client, existing_docs: Dict[str, str]):
    """Process files in batches with comprehensive error handling"""
    
    # Filter and validate files
    valid_files = []
    for file_path in changed_files:
        if not file_path.strip():
            continue
        
        if not file_path.endswith('.py'):
            logger.info(f"Skipping non-Python file: {file_path}")
            continue
        
        if Path(file_path).exists():
            valid_files.append(file_path.strip())
        else:
            logger.warning(f"File not found: {file_path}")
    
    if not valid_files:
        logger.info("No valid Python files to process")
        return {}, []
    
    logger.info(f"Processing {len(valid_files)} valid files in batches of {config.batch_size}")
    
    new_docs_generated = {}
    processing_errors = []
    
    # Process in batches
    for i in range(0, len(valid_files), config.batch_size):
        batch = valid_files[i:i + config.batch_size]
        batch_num = (i // config.batch_size) + 1
        total_batches = (len(valid_files) + config.batch_size - 1) // config.batch_size
        
        logger.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
        
        for file_path in batch:
            try:
                framework_name = get_framework_name(file_path)
                logger.info(f"Generating documentation for {framework_name} ({file_path})")
                
                # Generate documentation
                doc_content, error = create_documentation_with_retry(client, file_path, existing_docs)
                
                if doc_content and not error:
                    # Save documentation file
                    doc_file_path = f"docs/examples/{framework_name}-integration.md"
                    
                    success, write_error = write_file_content(doc_file_path, doc_content)
                    if success:
                        logger.info(f"Generated documentation: {doc_file_path}")
                        new_docs_generated[framework_name] = doc_file_path
                    else:
                        error_msg = f"Failed to write documentation for {file_path}: {write_error}"
                        logger.error(error_msg)
                        processing_errors.append(error_msg)
                else:
                    error_msg = f"Failed to generate documentation for {file_path}: {error}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)
                
                # Brief delay between files
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = f"Unexpected error processing {file_path}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                processing_errors.append(error_msg)
        
        # Delay between batches
        if batch_num < total_batches:
            logger.info(f"Batch {batch_num} complete, brief pause before next batch...")
            time.sleep(2)
    
    return new_docs_generated, processing_errors

def main():
    """Main execution with comprehensive error handling and monitoring"""
    start_time = datetime.now()
    logger.info("Starting enhanced documentation generation...")
    
    try:
        # Validate environment
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValidationError("ANTHROPIC_API_KEY environment variable not set")
        
        # Get changed files
        changed_files_str = os.environ.get('CHANGED_FILES', '')
        if not changed_files_str.strip():
            logger.info("No changed files provided")
            return
        
        changed_files = [f.strip() for f in changed_files_str.split('\n') if f.strip()]
        logger.info(f"Processing {len(changed_files)} changed files")
        
        # Create Claude client
        client, client_error = create_claude_client(api_key)
        if not client or client_error:
            raise DocumentationError(f"Failed to initialize Claude client: {client_error}")
        
        logger.info("Claude client initialized successfully")
        
        # Get existing documentation patterns
        existing_docs = get_existing_docs()
        logger.info(f"Loaded {len(existing_docs)} existing documentation files for pattern matching")
        
        # Process files in batches
        new_docs_generated, processing_errors = process_files_in_batches(
            changed_files, client, existing_docs
        )
        
        # Report processing results
        if processing_errors:
            logger.warning(f"Encountered {len(processing_errors)} processing errors:")
            for error in processing_errors[:5]:  # Limit error output
                logger.warning(f"  - {error}")
            if len(processing_errors) > 5:
                logger.warning(f"  ... and {len(processing_errors) - 5} more errors")
        
        # Update navigation if docs were generated
        if new_docs_generated:
            logger.info(f"Updating navigation for {len(new_docs_generated)} new documentation files")
            
            nav_success, nav_error = update_mkdocs_nav_safe(new_docs_generated)
            if nav_success:
                logger.info("Navigation updated successfully")
            else:
                logger.error(f"Failed to update navigation: {nav_error}")
                # Continue anyway - docs are still generated
            
            # Final success report
            duration = datetime.now() - start_time
            logger.info(f"\nDocumentation generation completed in {duration}")
            logger.info(f"Successfully generated {len(new_docs_generated)} documentation files:")
            for framework, path in new_docs_generated.items():
                logger.info(f"  {framework}: {path}")
            
            if processing_errors:
                logger.warning(f"Completed with {len(processing_errors)} errors")
        
        else:
            logger.info("No documentation files were generated")
            if processing_errors:
                logger.error("All processing attempts failed")
                sys.exit(1)
        
    except Exception as e:
        duration = datetime.now() - start_time
        logger.error(f"Documentation generation failed after {duration}")
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Create error summary
        error_summary = {
            'error': str(e),
            'duration': str(duration),
            'timestamp': datetime.now().isoformat()
        }
        
        # Save error details for debugging
        try:
            with open('.github/last-error.json', 'w') as f:
                json.dump(error_summary, f, indent=2)
        except:
            pass  # Don't fail on error logging failure
        
        sys.exit(1)

if __name__ == "__main__":
    main()