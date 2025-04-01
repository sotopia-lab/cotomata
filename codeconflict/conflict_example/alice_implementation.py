# Alice Code Base - alice_implementation.py

import torch
import torch.nn as nn
import math

# Import base classes from transformer_model.py
from transformer_model import MultiHeadAttention, PositionwiseFeedForward, EncoderLayer, TransformerEncoder

class TransformerModelWithAccumulation(nn.Module):
    def __init__(self, vocab_size, d_model=512, num_heads=8, d_ff=2048, num_layers=6, max_seq_len=5000, dropout=0.1):
        super().__init__()
        self.encoder = TransformerEncoder(vocab_size, d_model, num_heads, d_ff, num_layers, max_seq_len, dropout)
        self.output_layer = nn.Linear(d_model, vocab_size)
        
    def forward(self, x, mask=None):
        encoder_output = self.encoder(x, mask)
        output = self.output_layer(encoder_output)
        return output
        
    def train_model(self, dataloader, optimizer, criterion, epochs, accumulation_steps=1):
        self.train()
        for epoch in range(epochs):
            total_loss = 0
            optimizer.zero_grad()  # Reset gradients at the beginning of each epoch
            
            for i, batch in enumerate(dataloader):
                inputs, targets = batch
                
                # Move to GPU if available
                if torch.cuda.is_available():
                    inputs = inputs.cuda()
                    targets = targets.cuda()
                
                # Forward pass
                outputs = self(inputs)
                loss = criterion(outputs.view(-1, outputs.size(-1)), targets.view(-1))
                
                # Normalize loss to account for accumulation
                loss = loss / accumulation_steps
                print(loss)
                
                # Backward pass
                loss.backward()
                
                # Accumulate gradients for specified number of steps
                if (i + 1) % accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()
                
                total_loss += loss.item() * accumulation_steps
                
            # Handle any remaining gradients
            if len(dataloader) % accumulation_steps != 0:
                optimizer.step()
                optimizer.zero_grad()
                
            avg_loss = total_loss / len(dataloader)
            return avg_loss