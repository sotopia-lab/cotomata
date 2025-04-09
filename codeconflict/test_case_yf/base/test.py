import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from transformer import TransformerModel

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

if __name__ == "__main__":
    test_transformer_training()