# Domain-Specific Strategy Guidance

Each section below is a self-contained "Strategy Guidance" block ready to be inlined
into a generated program.md. The autoloop skill selects the appropriate block based
on the detected project type and user's optimization goal.

---

## ML / Deep Learning Training

Try these categories of changes, roughly in order of expected impact:

**Architecture tweaks**:
- Layer normalization placement (pre-norm vs post-norm vs RMSNorm)
- Attention variants (grouped-query, multi-query, sliding window)
- Activation functions (GELU, SwiGLU, ReLU²)
- Residual connection scaling
- Embedding tying (input/output weight sharing)

**Optimizer and learning rate**:
- AdamW beta values (especially beta2: try 0.95, 0.98, 0.99)
- Learning rate schedules (cosine, linear warmup+decay, WSD)
- Weight decay values
- Gradient clipping thresholds
- Warmup steps

**Regularization**:
- Dropout rates (attention, residual, embedding)
- Label smoothing
- Stochastic depth
- Gradient noise injection

**Initialization**:
- Scaling factors for residual branches
- Embedding initialization scale
- Output projection initialization

**Training recipe**:
- Batch size (if memory allows)
- Sequence length
- Gradient accumulation steps
- Mixed precision settings

**What worked in autoresearch's 126 experiments**: Norm scaling adjustments, AdamW beta2 tuning, residual scaling, initialization changes, and removing unnecessary complexity. Many "improvements" came from *removing* things. Simpler models often matched or beat complex ones.

---

## Test Coverage Improvement

Try these strategies to increase test coverage:

**Low-hanging fruit**:
- Find untested functions (check coverage report for 0% files)
- Add basic smoke tests for uncovered modules
- Test error paths (what happens when input is None, empty, wrong type?)
- Test boundary conditions (0, 1, max, negative, empty string)

**Systematic coverage**:
- Parameterized tests to cover multiple inputs with one test function
- Property-based testing (hypothesis for Python, fast-check for JS)
- Test each branch of conditional logic explicitly
- Cover exception handlers with tests that trigger the exception

**Integration gaps**:
- Test combinations of components that are individually tested
- Test configuration loading and validation
- Test CLI entry points and argument parsing
- Test error propagation across module boundaries

**Quality over quantity**:
- Each test should have a clear assertion (not just "doesn't crash")
- Test behavior, not implementation details
- Avoid testing trivial getters/setters — focus on logic
- One test per behavior, not one test per line of code

**Metric**: Use `pytest --cov --cov-report=term-missing` and extract the TOTAL coverage percentage. Alternatively, count the number of passing tests.

---

## Code Quality / Lint Score

Try these refactoring patterns to improve lint scores:

**Complexity reduction**:
- Extract long functions into smaller, named helpers
- Replace nested if/else chains with early returns
- Replace complex boolean expressions with named variables
- Simplify list comprehensions that are hard to read

**Type safety**:
- Add type annotations to function signatures
- Replace `Any` with specific types
- Use TypedDict for dictionary shapes
- Add return type annotations

**Code smells**:
- Remove unused imports and variables
- Replace magic numbers with named constants
- Consolidate duplicate code into shared functions
- Fix inconsistent naming conventions

**Documentation**:
- Add docstrings to public functions
- Document non-obvious parameters
- Add module-level docstrings

**Metric**: Use `ruff check --statistics` for Python, `eslint --format compact` for JS/TS. Count total issues or extract a score. Lower is better.

---

## Performance / Benchmarks

Try these optimization strategies:

**Algorithmic**:
- Replace O(n²) operations with O(n log n) or O(n) alternatives
- Use appropriate data structures (set for membership, dict for lookup)
- Avoid unnecessary copies of large data structures
- Use generators/iterators instead of materializing full lists

**Caching**:
- Memoize expensive pure functions
- Cache repeated computations in loops
- Use LRU cache for functions with limited input space
- Precompute values used in hot paths

**I/O optimization**:
- Batch database queries instead of N+1
- Use async I/O for network operations
- Buffer file writes
- Use memory-mapped files for large reads

**Language-specific**:
- Python: Use built-in functions (map, filter, sum) over manual loops; numpy for numeric work; avoid global variable lookup in hot paths
- Rust: Avoid unnecessary allocations, use iterators over collecting, prefer stack over heap
- JS/TS: Minimize DOM access, avoid creating closures in loops, use typed arrays for numeric work

**Metric**: Use `hyperfine`, `pytest-benchmark`, `cargo bench`, or `go test -bench`. Extract the median or mean execution time. Lower is better.

---

## Prompt Engineering

Try these prompt optimization strategies:

**Structure**:
- Add/remove few-shot examples (find the minimal effective set)
- Reorder sections (task description, constraints, examples, output format)
- Make output format more explicit (JSON schema, markdown template)
- Add chain-of-thought instructions ("think step by step")

**Instruction clarity**:
- Replace ambiguous terms with specific ones
- Add negative examples ("do NOT do X")
- Specify edge cases explicitly
- Quantify qualitative requirements ("at least 3 sentences")

**Context management**:
- Trim unnecessary context that dilutes attention
- Move critical instructions to beginning and end (primacy/recency effect)
- Use XML tags or markdown headers for clear section boundaries
- Add a "role" prefix to ground the model's behavior

**Sampling parameters**:
- Temperature: lower for factual, higher for creative
- Top-p/top-k: tighter for precision, looser for diversity
- Max tokens: set appropriate ceiling
- System prompt vs user prompt placement

**Metric**: Run eval suite and extract accuracy, F1, or human-preference score. Higher is better.

---

## Configuration Tuning

Try these parameter sweep strategies:

**Systematic exploration**:
- Binary search on numeric parameters (find the inflection point)
- Try order-of-magnitude jumps first, then refine
- Test one parameter at a time (isolate effects)
- After individual optimization, test combinations

**Common parameters**:
- Concurrency/parallelism limits (workers, threads, connections)
- Buffer sizes and queue depths
- Timeout values (connection, read, write, idle)
- Cache sizes and TTLs
- Retry counts and backoff parameters

**Load testing**:
- Verify metric under realistic load (not just idle)
- Check for resource leaks over time
- Test behavior at saturation point
- Measure tail latency (p99, p999) not just mean

**Safety rails**:
- Never set resource limits above what the hardware can handle
- Always keep some headroom for spikes
- Test that error handling still works at new settings
- Verify that changed config actually takes effect (not cached/overridden)

**Metric**: Latency (p50, p99), throughput (req/s), error rate, or resource utilization. Define "better" clearly — sometimes lower latency trades off with higher resource usage.
