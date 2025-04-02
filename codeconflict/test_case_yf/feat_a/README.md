# Feature A: Loss Plotting

## Description
This feature enhances the TransformerModel by adding functionality to plot training loss curves. The loss visualization helps in analyzing training performance and diagnosing potential issues like overfitting or learning rate problems.

## Implementation Details
- Added a new `_plot_loss()` helper method that creates and saves visual plots
- Added matplotlib integration for visualization

## Usage
```python
model = TransformerModel(...)
losses = model.train_model(
    dataloader=train_dataloader,
    optimizer=optimizer, 
    criterion=criterion, 
    epochs=5,
    plot_loss=True,              # Enable loss plotting (default: True)
    plot_path="my_loss_plot.png" # Custom path for the plot (default: "loss_plot.png")
)
```

## Output
The feature generates a figure with:
1. Training Loss (All Batches): Shows the loss value for each batch

The plot is saved to the specified path (default: "loss_plot.png").

## Testing
Run the test file to verify this feature:
```
python test.py
```