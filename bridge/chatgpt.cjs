const { app, safeStorage, shell } = require("electron");
const { join } = require("node:path");
const { readFileSync } = require("node:fs");
const { pathToFileURL } = require("node:url");

app.setName("MuseCapsule Connection Check");

async function main () {
    const request = JSON.parse(readFileSync(0, "utf8"));

    if (
        request === null ||
        typeof request !== "object" ||
        typeof request.text !== "string" ||
        !request.text.trim()
    ) {
        throw new Error("Request text must be a nonblank string.");
    }

    for (const field of ["instructions", "model"]) {
        if (typeof request[field] !== "string" || !request[field].trim()) {
            throw new Error(`Request ${field} must be a nonblank string.`);
        }
    }


    await app.whenReady();

    // Load the SDK from the explicitly configured DevKit installation.
    const devkitDir = process.argv[2];

    if (!devkitDir) {
        throw new Error("DevKit directory argument is required.");
    }

    const sdkUrl = pathToFileURL(
        join(devkitDir, "packages", "local", "dist", "index.js"),
    );

    const { createChatGPT } = await import(sdkUrl.href);

    const chatgpt = createChatGPT({
        appName: "MuseCapsule Connection Check",
        appId: "musecapsule-connection-check",
        redirectPort: 0,
        sendHostId: true,
        storageDir: join(app.getPath("appData"), "musecapsule-connection-check"),
        openBrowser: (url) => shell.openExternal(url),
        credentialEncryption: {
            id: "electron-safe-storage-v1",
            isAvailable: () => safeStorage.isEncryptionAvailable(),
            encrypt: (text) => safeStorage.encryptString(text),
            decrypt: (bytes) => safeStorage.decryptString(Buffer.from(bytes)),
        },
    });

    let session = await chatgpt.getSession();

    if (session.status !== "connected") {
        console.error("Opening ChatGPT sign-in...");
        session = await chatgpt.signIn();
    }

    console.error("Status:", session.status);
    console.error("ChatGPT plan usage enabled:", session.sharing);

    if (!session.sharing) {
        throw new Error("ChatGPT plan usage was not enabled.");
    }

    const models = await chatgpt.listModels({
        signal: AbortSignal.timeout(30_000),
    });


    console.error("Available models:", models.map((model) => model.slug));

    const model = models.find((item) => item.slug === request.model);

    if (!model) {
        throw new Error("Requested model is unavailable for this account.");
    }

    // Send one small request to verify inference access.
    const result = await chatgpt.streamResponse({
        model: model.slug,
        instructions: request.instructions,
        input: request.text,
        signal: AbortSignal.timeout(60_000),
    });

    // Reserve stdout for the model response consumed by Python.
    process.stdout.write(`${result.text}\n`);
}

main()
    .then(() => app.quit())
    .catch((error) => {
        console.error(error.code ?? "connection_check_failed", error.message);
        app.exit(1);
    });
