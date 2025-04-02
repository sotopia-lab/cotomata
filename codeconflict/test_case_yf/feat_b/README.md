# Feature B: Model Checkpoint Saving

## Description
This feature adds the ability to save model checkpoints during training. This is crucial for preserving training progress, especially for long-running training sessions, and enables model sharing and deployment.

## Implementation Details
- Implemented `save_checkpoint()` method to save model state, configuration, and training state
- Enhanced `train_model()` to automatically save checkpoints at specified intervals
- Checkpoints include:
  - Model state dictionary
  - Model configuration
  - Optimizer state (when available)
  - Current loss information

## Usage

### Training with automatic checkpoints
```python
model = TransformerModel(...)

losses = model.train_model(
    dataloader=train_dataloader,
    optimizer=optimizer, 
    criterion=criterion, 
    epochs=10,
    save_dir="my_checkpoints",  # Directory to save checkpoints (default: "checkpoints")
    save_every=2                # Save checkpoint every N epochs (default: 1)
)
```

### Manually saving a checkpoint
```python
model.save_checkpoint(
    path="path/to/checkpoint.pt",
    optimizer=optimizer,      # Optional
    epoch=current_epoch,      # Optional
    loss=current_loss         # Optional
)
```

# Restore optimizer state if needed
optimizer = torch.optim.Adam(model.parameters())
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

# Extract training information
epoch = checkpoint['epoch']
loss = checkpoint['loss']
```

## Testing
Run the test file to verify this feature:
```
python test.py
```