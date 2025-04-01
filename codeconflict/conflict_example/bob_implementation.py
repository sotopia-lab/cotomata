# Bob Code Base - bob_implementation.py
import torch
import torch.nn as nn
import math

# Import base classes from transformer_model.py
from transformer_model import MultiHeadAttention, PositionwiseFeedForward, EncoderLayer, TransformerEncoder

class TransformerModelWithAMP(nn.Module):
    def __init__(self, vocab_size, d_model=512, num_heads=8, d_ff=2048, num_layers=6, max_seq_len=5000, dropout=0.1):
        super().__init__()
        self.encoder = TransformerEncoder(vocab_size, d_model, num_heads, d_ff, num_layers, max_seq_len, dropout)
        self.output_layer = nn.Linear(d_model, vocab_size)
        
    def forward(self, x, mask=None):
        encoder_output = self.encoder(x, mask)
        output = self.output_layer(encoder_output)
        return output
        
    def train_model(self, dataloader, optimizer, criterion, epochs):
        # Use AMP if CUDA is available, otherwise fallback to normal training
        use_amp = torch.cuda.is_available()
        
        if use_amp:
            from torch.cuda.amp import autocast, GradScaler
            scaler = GradScaler()
            print("Using Automatic Mixed Precision training")
        else:
            print("CUDA not available, falling back to normal precision training")
        
        self.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                inputs, targets = batch
                
                # Move to GPU if available
                if torch.cuda.is_available():
                    inputs = inputs.cuda()
                    targets = targets.cuda()
                
                # Forward pass with mixed precision if CUDA is available
                if use_amp:
                    with autocast():
                        outputs = self(inputs)
                        loss = criterion(outputs.view(-1, outputs.size(-1)), targets.view(-1))
                    
                    # Backward and optimize with gradient scaling
                    optimizer.zero_grad()
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    # Normal precision training on CPU
                    outputs = self(inputs)
                    loss = criterion(outputs.view(-1, outputs.size(-1)), targets.view(-1))
                    
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                
                total_loss += loss.item()
                
            avg_loss = total_loss / len(dataloader)
            return avg_loss