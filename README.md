# NuGetReflector

This tool mirrors an NuGet repository to another NuGet server. This can be used to clone public repositories or used to make private repositories redundant.

---

# Install

### Needs:

* Python >= 2.7
* Python < 3 
* Pip

```shell
cp config/config.example.conf config/config.conf;
vi config/config.conf; # Fill out your settings
pip install -r requirements.txt;
```

# Usage:

```shell
python reflector.py;
```