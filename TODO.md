# TODO

## Discriminator metadata refinements

- [ ] Audit current `Discriminator` metadata contract:
  - Document how `default` behaves during facade normalization.
  - Clarify when `allow_missing` falls back to facade defaults versus raising.
- [ ] Design separate hooks for unresolved selectors:
  - `on_missing`: selector omitted; allow specifying a fallback selector value and dispatch target that may differ from the facade default.
  - `on_mismatch`: selector provided but unmatched; support routing to either the facade (using its default payload) or an alternate subclass.
- [ ] Consider distinguishing between facade default instantiation and subclass dispatch:
  - Ensure defaults can instantiate the facade itself when appropriate.
  - Allow defaulted selectors to point to explicit subclasses without requiring manual overrides.
- [ ] Capture test scenarios for each combination (missing selector, mismatched selector, explicit default routing).
