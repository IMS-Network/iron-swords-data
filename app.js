const express = require("express");
const path = require("path");
const fs = require("fs-extra");
const marked = require("marked");

const app = express();
const PORT = 3000;

// Paths
const MARKDOWN_DIR = path.join(__dirname, "IDFspokesman");
const PUBLIC_DIR = path.join(__dirname, "public");

// Middleware for static files
app.use(express.static(PUBLIC_DIR));

// Serve the homepage with a dynamic navbar
app.get("/", async (req, res) => {
    const fileStructure = await generateFileStructure(MARKDOWN_DIR);
    res.render("layout", { fileStructure, content: "<h1>Welcome to the Markdown Browser</h1>" });
});

// Serve Markdown files
app.get("/files/*", async (req, res) => {
    const filePath = path.join(MARKDOWN_DIR, req.params[0]);
    if (fs.existsSync(filePath) && filePath.endsWith(".md")) {
        const markdown = await fs.readFile(filePath, "utf-8");
        const htmlContent = marked.parse(markdown);
        const fileStructure = await generateFileStructure(MARKDOWN_DIR);
        res.render("layout", { fileStructure, content: htmlContent });
    } else {
        res.status(404).send("File not found");
    }
});

// Helper function to generate the file structure
async function generateFileStructure(rootDir) {
    const fileStructure = {};

    async function recurse(dir, obj) {
        const items = await fs.readdir(dir);
        for (const item of items) {
            const itemPath = path.join(dir, item);
            const stats = await fs.stat(itemPath);

            if (stats.isDirectory()) {
                obj[item] = {};
                await recurse(itemPath, obj[item]);
            } else if (stats.isFile() && item.endsWith(".md")) {
                const relativePath = path.relative(rootDir, itemPath).replace(/\\/g, "/");
                const parts = relativePath.split("/");

                const year = parts[0];
                const month = parts[1];
                const day = parts[2];

                obj[year] = obj[year] || {};
                obj[year][month] = obj[year][month] || {};
                obj[year][month][day] = obj[year][month][day] || [];
                
                // Ensure it's an array
                if (!Array.isArray(obj[year][month][day])) {
                    console.error(`Day is not an array: ${JSON.stringify(obj[year][month][day])}`);
                    obj[year][month][day] = [];
                }

                obj[year][month][day].push({
                    name: item.replace(".md", ""),
                    url: `/files/${relativePath}`,
                });
            }
        }
    }

    await recurse(rootDir, fileStructure);
    return fileStructure;
}

// Set view engine
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
