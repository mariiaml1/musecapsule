## ChatGPT image extraction demo

The demo calls ChatGPT through a local Electron bridge, validates the
response with Pydantic, verifies source quotes, and updates session state.

### Requirements

- Python 3.13
- Node.js >= 22.12
- macOS (the currently tested platform)
- An eligible ChatGPT account with ChatGPT plan usage enabled

### Set up the ChatGPT DevKit

Run these commands from the directory containing your MuseCapsule checkout:

```bash
git clone https://github.com/openai/sign-in-with-chatgpt-devkit.git
cd sign-in-with-chatgpt-devkit
git checkout --detach 0a36fefeb913055c8c7a1a29b63d82b96b2e841a
npm ci
npm run build -w @siwc/local
```

Only the local SDK needs to be built. The Paste Perfect desktop example
is not required.

### Run the demo

From the MuseCapsule project root, with the Python environment activated:

```bash
python -m pip install -e ".[dev]"
python -m musecapsule.demo --devkit-dir ../sign-in-with-chatgpt-devkit
```

On first use, a browser opens for ChatGPT authorization. Credentials are
stored outside the repository and encrypted using macOS Keychain-backed
Electron safeStorage.

The demo makes a live model request and consumes ChatGPT plan allowance.

### Current limitations

- Extracts images from one demo message.
- Uses prompted JSON with application-side validation; schema-constrained
  generation is not yet implemented.
- Image boundaries and labels may vary between requests.
- Uses the first model returned by the SDK.
- Requires a separate DevKit checkout.
- Does not yet persist sessions or orchestrate the four planned agent roles.
