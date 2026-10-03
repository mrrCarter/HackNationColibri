"""Sauti domain core (Claude Domain lane).

Business truth and owner control: action envelopes, exact approval bound to a
content digest and a trusted owner context, state transitions that separate
business status from transport status, deterministic evidence validation and
counts, and calendar constraints. No model call lives here. Everything an
LLM produces enters this package as data to be validated, never as authority.
"""
