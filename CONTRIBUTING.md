# Contributing

Thanks for your interest in this project! To contribute:


Fork, then clone the repo:

```bash
git clone git@github.com:your-username/NuGetReflector.git;
```

Make sure your version of python is version 2 at least version `2.7` preferably `2.7.13` and you have pip.

Install python libraries:

```bash
pip install -r requirements.txt;
```

Install the [DotNet CLI](https://github.com/dotnet/cli), and make note of the `dotnet` binary path.

Create a new config and edit it:

```bash
cp config/config.example.yaml config/config.yaml;
vi config/config.yaml;
```

Config options can be found on the [README](README.md).

Make your changes...

Push to your fork and [submit a pull request][pr].

[pr]: https://github.com/MelonSmasher/NuGetReflector/compare/

At this point you're waiting on me. I'll do my best to review all pull requests when I have the time. 

