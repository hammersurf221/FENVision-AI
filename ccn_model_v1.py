import torch
import torch.nn as nn
import torch.nn.functional as F

class CCN(nn.Module):
    def __init__(self, num_classes=13):
        super(CCN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=5, padding=2)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.dropout = nn.Dropout(0.3)

        # New layers
        self.global_pool = nn.AdaptiveAvgPool2d((8, 8))  # Always outputs [B, 128, 8, 8]
        self.fc = nn.Conv2d(128, num_classes, kernel_size=1)  # Reduces channels to 13

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2)  # → [B, 32, 128, 128]
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)  # → [B, 64, 64, 64]
        x = F.relu(self.conv3(x))
        x = F.max_pool2d(x, 2)  # → [B, 128, 32, 32]

        x = self.dropout(x)
        x = self.global_pool(x)  # → [B, 128, 8, 8]
        x = self.fc(x)           # → [B, 13, 8, 8]
        x = x.permute(0, 2, 3, 1)  # → [B, 8, 8, 13] (for CrossEntropyLoss)

        return x
