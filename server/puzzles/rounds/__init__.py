# TODO: Ideally all of these one-off methods would be refactored into a class
# implementing each of normalization, validation, answer checking, etc.
# But we don't have time for that, so one-off methods will have to do.

# Mapping from round slug to custom normalizer.
CUSTOM_ROUND_ANSWERS = {}

# Mapping from round slug to custom answer checker.
# Answer checkers happen AFTER normalization. In most cases you should use normalization
# first to transform what the output solvers will see, but in some cases we want
# to be extra lenient (but not show them the transformation unless it's correct).
CUSTOM_ROUND_CHECKERS = {}

# Mapping from round slug to custom answer validator.
CUSTOM_ROUND_VALIDATORS = {}

# Mapping from round slug to callback when a puzzle is solved.
CUSTOM_ROUND_SOLVE_CALLBACKS = {}

# Mapping from round slug to custom rate limit.
CUSTOM_RATE_LIMITERS = {}
