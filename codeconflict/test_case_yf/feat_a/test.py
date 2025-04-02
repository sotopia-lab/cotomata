import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from transformer import TransformerModel
import os
import matplotlib
# Force matplotlib to not use any Xwindows backend (useful for servers without GUI)
matplotlib.use('Agg')

def test_transformer_training():
    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Set hyperparameters
    vocab_size = 1000
    batch_size = 16
    seq_length = 20
    
    # Create a small dummy dataset
    # Random sequences of integers (representing token ids)
    inputs = torch.randint(1, vocab_size, (100, seq_length))
    targets = torch.randint(1, vocab_size, (100, seq_length))
    
    # Create dataloader
    dataset = TensorDataset(inputs, targets)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Initialize the model
    model = TransformerModel(
        vocab_size=vocab_size,
        d_model=64,      # Smaller for testing
        num_heads=4,     # Smaller for testing
        d_ff=128,        # Smaller for testing
        num_layers=2,    # Fewer layers for testing
        max_seq_len=50,
        dropout=0.1
    ).to(device)
    
    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Train for a few epochs
    epochs = 2
    losses = model.train_model(dataloader, optimizer, criterion, epochs)
    
    # Simple test to ensure loss decreases
    assert losses[-1] < losses[0], "Training loss should decrease"
    
    print("Basic training test passed!")

def test_transformer_training_with_plot():
    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Set hyperparameters
    vocab_size = 1000
    batch_size = 16
    seq_length = 20
    
    # Create a small dummy dataset
    # Random sequences of integers (representing token ids)
    inputs = torch.randint(1, vocab_size, (100, seq_length))
    targets = torch.randint(1, vocab_size, (100, seq_length))
    
    # Create dataloader
    dataset = TensorDataset(inputs, targets)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Initialize the model
    model = TransformerModel(
        vocab_size=vocab_size,
        d_model=64,      # Smaller for testing
        num_heads=4,     # Smaller for testing
        d_ff=128,        # Smaller for testing
        num_layers=2,    # Fewer layers for testing
        max_seq_len=50,
        dropout=0.1
    ).to(device)
    
    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Test plot path
    plot_path = "test_loss_plot.png"
    
    # Clean up any existing test files
    if os.path.exists(plot_path):
        os.remove(plot_path)
    
    # Train for a few epochs
    epochs = 2
    losses = model.train_model(
        dataloader, 
        optimizer, 
        criterion, 
        epochs, 
        plot_loss=True, 
        plot_path=plot_path
    )
    
    # Tests
    
    # Test 1: Check if plot file was created
    assert os.path.exists(plot_path), f"Loss plot file {plot_path} should be created"
    
    # Test 2: Check if plot file has content (size > 0)
    assert os.path.getsize(plot_path) > 0, f"Loss plot file {plot_path} should have content"
    
    print("Plot test passed!")
    
    # Clean up test files
    if os.path.exists(plot_path):
        os.remove(plot_path)

if __name__ == "__main__":
    test_transformer_training()
    test_transformer_training_with_plot()