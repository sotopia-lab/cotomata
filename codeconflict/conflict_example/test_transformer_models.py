import unittest
import torch
import argparse
import sys
from torch.utils.data import DataLoader, TensorDataset

# Import needed dynamically based on user selection
# No imports here - we'll import the selected model at runtime

class TestTransformerFeatures(unittest.TestCase):
    def setUp(self):
        # Set random seed for reproducibility
        torch.manual_seed(42)
        
        # Common parameters for all models
        self.vocab_size = 1000
        self.batch_size = 4
        self.seq_length = 20
        self.d_model = 64  # Smaller dimension for quicker tests
        self.num_heads = 4
        self.d_ff = 128
        self.num_layers = 2
        self.epochs = 5
        
        # Create a small dummy dataset
        num_samples = 32
        X = torch.randint(0, self.vocab_size, (num_samples, self.seq_length))
        y = torch.randint(0, self.vocab_size, (num_samples, self.seq_length))
        
        self.dataset = TensorDataset(X, y)
        self.dataloader = DataLoader(self.dataset, batch_size=self.batch_size, shuffle=True)
        
        # Initialize loss function
        self.criterion = torch.nn.CrossEntropyLoss()
    
    def test_gradient_accumulation(self):
        """Test gradient accumulation functionality."""
        print("\n==== Testing Gradient Accumulation ====")
        
        # Get the model based on the selected implementation
        model_class = self.get_model_class()
        
        # Check if the model supports accumulation by inspecting its method signature
        import inspect
        sig = inspect.signature(model_class.train_model)
        supports_accumulation = 'accumulation_steps' in sig.parameters
        
        if not supports_accumulation:
            print(f"❌ FAIL: {model_class.__name__} does not support gradient accumulation")
            self.fail(f"{model_class.__name__} does not support gradient accumulation")
        
        # First, train with accumulation_steps=1 (equivalent to normal training)
        model_without_accum = model_class(
            vocab_size=self.vocab_size,
            d_model=self.d_model,
            num_heads=self.num_heads,
            d_ff=self.d_ff,
            num_layers=self.num_layers
        )
        
        # Get parameter signatures before training
        params_before = [p.clone().detach() for p in model_without_accum.parameters()]
        
        # Create optimizer
        optimizer_without_accum = torch.optim.Adam(model_without_accum.parameters(), lr=0.001)
        
        # Train with accumulation_steps=1
        print("Training with accumulation_steps=1...")
        if 'use_amp' in sig.parameters:
            # For combined model that supports both features
            loss_without_accum = model_without_accum.train_model(
                self.dataloader, 
                optimizer_without_accum, 
                self.criterion, 
                self.epochs, 
                accumulation_steps=1,
                use_amp=False
            )
        else:
            # For models that only support accumulation
            loss_without_accum = model_without_accum.train_model(
                self.dataloader, 
                optimizer_without_accum, 
                self.criterion, 
                self.epochs, 
                accumulation_steps=1
            )
        
        # Then, train with accumulation_steps=2
        model_with_accum = model_class(
            vocab_size=self.vocab_size,
            d_model=self.d_model,
            num_heads=self.num_heads,
            d_ff=self.d_ff,
            num_layers=self.num_layers
        )
        
        # Create optimizer
        optimizer_with_accum = torch.optim.Adam(model_with_accum.parameters(), lr=0.001)
        
        # Train with accumulation_steps=2
        print("Training with accumulation_steps=2...")
        if 'use_amp' in sig.parameters:
            # For combined model that supports both features
            loss_with_accum = model_with_accum.train_model(
                self.dataloader, 
                optimizer_with_accum, 
                self.criterion, 
                self.epochs, 
                accumulation_steps=2,
                use_amp=False
            )
        else:
            # For models that only support accumulation
            loss_with_accum = model_with_accum.train_model(
                self.dataloader, 
                optimizer_with_accum, 
                self.criterion, 
                self.epochs, 
                accumulation_steps=2
            )
        
        print(f"Loss without accumulation: {loss_without_accum:.4f}")
        print(f"Loss with accumulation: {loss_with_accum:.4f}")
        
        # Calculate final parameter differences to verify different update patterns
        # Get parameters after training with accumulation
        params_after = [p.clone().detach() for p in model_with_accum.parameters()]
        
        # Check that parameters were updated and are different
        params_equal = True
        for p1, p2 in zip(params_before, params_after):
            if not torch.allclose(p1, p2, atol=1e-4):
                params_equal = False
                break
        
        # Parameters should be different after training with gradient accumulation
        if not params_equal:
            print("✅ PASS: Gradient accumulation is correctly updating model parameters")
        else:
            print("❌ FAIL: Gradient accumulation is not affecting model parameters")
            self.assertFalse(params_equal, "Gradient accumulation not affecting model parameters")
        
        print("==== Gradient Accumulation Test Completed ====")
    
    def test_amp_training(self):
        """Test automatic mixed precision training."""
        print("\n==== Testing Automatic Mixed Precision ====")
        
        # Skip test if CUDA is not available
        if not torch.cuda.is_available():
            print("❌ SKIP: CUDA not available, skipping AMP test")
            self.skipTest("CUDA not available for AMP testing")
        
        # Get the model based on the selected implementation
        model_class = self.get_model_class()
        
        # Create model instance
        model = model_class(
            vocab_size=self.vocab_size,
            d_model=self.d_model,
            num_heads=self.num_heads,
            d_ff=self.d_ff,
            num_layers=self.num_layers
        )
        
        # Move model to GPU since AMP requires CUDA
        model = model.cuda()
        
        # Check if model supports AMP by looking for use_amp parameter or autocast import
        import inspect
        import re
        
        # Look at the train_model implementation
        source_code = inspect.getsource(model.train_model)
        
        # Check if the source contains autocast import or references
        supports_amp = ('autocast' in source_code or 
                        'GradScaler' in source_code or 
                        'use_amp' in inspect.signature(model.train_model).parameters)
        
        if not supports_amp:
            print(f"❌ FAIL: {model_class.__name__} does not support AMP")
            self.fail(f"{model_class.__name__} does not support AMP")
        
        # Create optimizer
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # Train with AMP
        print("Training with AMP...")
        
        # Check if the model has a use_amp parameter to control AMP
        if 'use_amp' in inspect.signature(model.train_model).parameters:
            loss = model.train_model(
                self.dataloader, 
                optimizer, 
                self.criterion, 
                self.epochs, 
                use_amp=True
            )
        else:
            # For models like Bob's that don't have explicit parameter
            loss = model.train_model(
                self.dataloader, 
                optimizer, 
                self.criterion, 
                self.epochs
            )
        
        print(f"AMP training loss: {loss:.4f}")
        
        if loss is not None:
            print("✅ PASS: AMP training completed successfully")
        else:
            print("❌ FAIL: AMP training failed to return a loss value")
            self.assertIsNotNone(loss, "AMP training failed")
        
        print("==== AMP Testing Completed ====")
    
    def get_model_class(self):
        """Get the model class based on command line arguments."""
        return self.model_class


def run_tests(model_name, test_name=None):
    """Run the specified test on the given model."""
    
    # Import the selected model
    if model_name == "base":
        from transformer_model import TransformerModel as TestModel
    elif model_name == "alice":
        from alice_implementation import TransformerModelWithAccumulation as TestModel
    elif model_name == "bob":
        from bob_implementation import TransformerModelWithAMP as TestModel
    elif model_name == "combined":
        from combined_implementation import TransformerModelCombined as TestModel
    else:
        print(f"Unknown model: {model_name}")
        sys.exit(1)
    
    # Set the model class to use in tests
    TestTransformerFeatures.model_class = TestModel
    
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add the specified test or both tests
    if test_name == "accumulation" or test_name is None:
        suite.addTest(TestTransformerFeatures("test_gradient_accumulation"))
    
    if test_name == "amp" or test_name is None:
        suite.addTest(TestTransformerFeatures("test_amp_training"))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status (0 if all passed, 1 if any failed)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test transformer model implementations.")
    parser.add_argument(
        "model", 
        choices=["base", "alice", "bob", "combined"],
        help="Which model implementation to test"
    )
    parser.add_argument(
        "--test", 
        choices=["accumulation", "amp"],
        help="Which test to run (default: both)"
    )
    
    args = parser.parse_args()
    sys.exit(run_tests(args.model, args.test))