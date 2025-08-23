# Claude Code Memory & Context Optimization Rules

## Context Window Management

### Priority Levels
1. **CRITICAL** - Always retain
   - Current task requirements
   - Active file being edited
   - Error messages and stack traces
   - Security considerations

2. **HIGH** - Retain during task
   - Related file contents
   - Import/dependency chains
   - Test files for code being modified
   - Recent command outputs

3. **MEDIUM** - Retain if relevant
   - Documentation snippets
   - Configuration files
   - Similar code patterns
   - Previous successful approaches

4. **LOW** - Discard after use
   - File listings
   - Search results after finding target
   - Completed task details
   - Old error messages

## Memory Optimization Strategies

### 1. Selective Reading
```
Instead of: Read entire file
Better: Read specific functions/classes/sections
Best: Read only the lines being modified + context
```

### 2. Progressive Exploration
```
Step 1: Glob for file patterns
Step 2: Grep for specific content
Step 3: Read only matched files
Step 4: Focus on relevant sections
```

### 3. Context Pruning Rules
- After reading a file for reference → Keep only relevant functions
- After successful search → Discard non-matching results
- After fixing an error → Keep only the solution, not attempts
- After completing a task → Clear working memory

## Smart Caching Patterns

### What to Remember
- Project structure (one-time scan)
- Common file locations
- Established patterns and conventions
- Successful command sequences
- User preferences and style

### What to Forget
- Temporary file contents
- Intermediate search results
- Failed attempt details
- Redundant information
- Implementation details after abstraction

## Efficient Search Strategies

### Pattern 1: Narrow First
```bash
# Good - Narrow search
**/*controller*.ts → Read specific methods

# Bad - Broad search
**/*.ts → Read everything
```

### Pattern 2: Parallel Discovery
```bash
# Execute simultaneously:
- Find all test files
- Locate configuration
- Search for dependencies
- Check documentation
```

### Pattern 3: Early Termination
```bash
# Stop searching once found:
- Use head_limit in grep
- Return on first match
- Limit directory depth
```

## Token Usage Optimization

### Reduce Input Tokens
- Use summaries instead of full content
- Extract only relevant code blocks
- Skip comments and documentation when not needed
- Ignore generated/compiled files

### Reduce Output Tokens
- Be concise (1-3 sentences max)
- Use code instead of explanations
- Skip unnecessary confirmations
- Avoid repeating information

## Working Memory Rules

### During Task Execution
**KEEP:**
- Current file being edited
- Related test files
- Import dependencies
- Error messages

**DISCARD:**
- Other project files
- Previous task context
- Successful operations
- Exploratory searches

### Between Tasks
**RESET:**
- Clear all file contents
- Reset assumptions
- Clear error history
- Forget temporary patterns

**RETAIN:**
- Project structure knowledge
- Coding conventions
- User preferences
- Successful patterns

## Intelligent Batching

### Batch Operations
```yaml
Good Batching:
  - Read 3-5 related files together
  - Run multiple searches in parallel
  - Execute related commands together
  - Apply multiple edits in sequence

Avoid:
  - Reading files one by one
  - Sequential searches
  - Redundant operations
  - Repeated file access
```

## Context Window Alerts

### Warning Signs
- Reading files > 500 lines
- Keeping > 10 files in memory
- Repeating same searches
- Accumulating error messages
- Growing response length

### Remediation Actions
- Summarize and discard
- Focus on specific sections
- Clear completed items
- Reset working memory
- Use more specific queries

## Performance Metrics

### Track and Optimize
- File reads per task: Target < 5
- Search operations per task: Target < 3
- Context size per operation: Target < 10KB
- Response length: Target < 500 tokens
- Task completion time: Minimize

## Advanced Techniques

### 1. Semantic Compression
- Replace code with descriptions
- Use placeholders for repetitive patterns
- Summarize instead of quoting

### 2. Lazy Loading
- Read files only when needed
- Defer searches until required
- Load configurations on demand

### 3. Smart Forgetting
- Clear after successful operations
- Prune irrelevant branches
- Compress historical context

### 4. Pattern Learning
- Remember successful approaches
- Cache common solutions
- Build mental models

## Session Management

### Start of Session
1. Scan project structure once
2. Identify key directories
3. Note technology stack
4. Check for configurations

### During Session
1. Focus on current task
2. Maintain minimal context
3. Clear completed work
4. Optimize searches

### End of Task
1. Verify completion
2. Clear working memory
3. Retain learnings
4. Reset for next task