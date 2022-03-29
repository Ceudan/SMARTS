import gym
import torch
import torch.nn as nn

from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class CFEDreamer(BaseFeaturesExtractor):
    """
    :param observation_space: (gym.Space)
    :param features_dim: (int) Number of features extracted.
        This corresponds to the number of unit for the last layer.
    """

    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = 512):
        super(CFEDreamer, self).__init__(observation_space, features_dim)
        # We assume CxHxW images (channels first)
        # Re-ordering will be done by pre-preprocessing or wrapper
        n_input_channels = observation_space.shape[0]
        self.cnn = nn.Sequential(
            nn.Conv2d(
                in_channels=n_input_channels,
                out_channels=48,
                kernel_size=4,
                stride=2,
                padding=0,
            ),
            nn.ELU(),
            nn.Conv2d(
                in_channels=48, out_channels=96, kernel_size=4, stride=2, padding=0
            ),
            nn.ELU(),
            nn.Conv2d(
                in_channels=96, out_channels=192, kernel_size=4, stride=2, padding=0
            ),
            nn.ELU(),
            nn.Conv2d(
                in_channels=192, out_channels=384, kernel_size=4, stride=2, padding=0
            ),
            nn.ELU(),
            nn.Flatten(),
        )

        # Compute shape by doing one forward pass
        with torch.no_grad():
            n_flatten = self.cnn(
                torch.as_tensor(observation_space.sample()[None]).float()
            ).shape[1]

        self.linear = nn.Sequential(nn.Linear(n_flatten, features_dim), nn.ELU())

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        return self.linear(self.cnn(observations))


class CFEL5Kit(BaseFeaturesExtractor):
    """Custom feature extractor from raster images for the RL Policy.
    :param observation_space: the input observation space
    :param features_dim: the number of features to extract from the input
    :param model_arch: the model architecture used to extract the features
    """

    def __init__(self, observation_space: gym.spaces.Dict, features_dim: int = 256,
                 model_arch: str = "simple_gn"):
        super(CFEL5Kit, self).__init__(observation_space, features_dim)

        # We assume CxHxW images (channels first)
        # Re-ordering will be done by pre-preprocessing or wrapper
        num_input_channels = observation_space["image"].shape[0]

        if model_arch == 'simple_gn':
            # A simplified feature extractor with GroupNorm.
            model = SimpleCNN_GN(num_input_channels, features_dim)
        else:
            raise NotImplementedError

        extractors = {"image": model}
        self.extractors = nn.ModuleDict(extractors)
        self._features_dim = features_dim

    def forward(self, observations: gym.spaces.Dict) -> torch.Tensor:
        encoded_tensor_list = []

        # self.extractors contain nn.Modules that do all the processing.
        for key, extractor in self.extractors.items():
            encoded_tensor_list.append(extractor(observations[key]))
        # Return a (B, self._features_dim) PyTorch tensor, where B is batch dimension.
        return torch.cat(encoded_tensor_list, dim=1)

def SimpleCNN_GN(num_input_channels: int, features_dim: int) -> nn.Module:
    """A simplified feature extractor with GroupNorm.
    :param num_input_channels: the number of input channels in the input
    :param features_dim: the number of features to extract from input
    """
    model = nn.Sequential(
        nn.Conv2d(num_input_channels, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False),
        nn.GroupNorm(4, 64),
        nn.ReLU(),
        nn.MaxPool2d(kernel_size=2, stride=2),
        nn.Conv2d(64, 32, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False),
        nn.GroupNorm(2, 32),
        nn.ReLU(),
        nn.MaxPool2d(kernel_size=2, stride=2),
        nn.Flatten(),
        nn.Linear(in_features=1568, out_features=features_dim),
    )

    return model


# class NatureCNN(BaseFeaturesExtractor):
#     """
#     CNN from DQN nature paper:
#         Mnih, Volodymyr, et al.
#         "Human-level control through deep reinforcement learning."
#         Nature 518.7540 (2015): 529-533.

#     :param observation_space:
#     :param features_dim: Number of features extracted.
#         This corresponds to the number of unit for the last layer.
#     """

#     def __init__(self, observation_space: gym.spaces.Box, features_dim: int = 512):
#         super(NatureCNN, self).__init__(observation_space, features_dim)
#         # We assume CxHxW images (channels first)
#         # Re-ordering will be done by pre-preprocessing or wrapper
#         assert is_image_space(observation_space, check_channels=False), (
#             "You should use NatureCNN "
#             f"only with images not with {observation_space}\n"
#             "(you are probably using `CnnPolicy` instead of `MlpPolicy` or `MultiInputPolicy`)\n"
#             "If you are using a custom environment,\n"
#             "please check it using our env checker:\n"
#             "https://stable-baselines3.readthedocs.io/en/master/common/env_checker.html"
#         )
#         n_input_channels = observation_space.shape[0]
#         self.cnn = nn.Sequential(
#             nn.Conv2d(n_input_channels, 32, kernel_size=8, stride=4, padding=0),
#             nn.ReLU(),
#             nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=0),
#             nn.ReLU(),
#             nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=0),
#             nn.ReLU(),
#             nn.Flatten(),
#         )

#         # Compute shape by doing one forward pass
#         with th.no_grad():
#             n_flatten = self.cnn(th.as_tensor(observation_space.sample()[None]).float()).shape[1]

#         self.linear = nn.Sequential(nn.Linear(n_flatten, features_dim), nn.ReLU())

#     def forward(self, observations: th.Tensor) -> th.Tensor:
#         return self.linear(self.cnn(observations))