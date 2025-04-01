# Test Alice's gradient accumulation implementation
python test_transformer_models.py alice --test accumulation

# Test Bob's AMP implementation
python test_transformer_models.py bob --test amp

# Test the combined implementation (runs both tests)
python test_transformer_models.py combined

# Test the base model (expected to fail both tests)
python test_transformer_models.py base