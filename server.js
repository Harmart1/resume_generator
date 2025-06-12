const express = require("express");
const multer = require("multer");
const cors = require("cors");

const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());

const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Resume Upload Endpoint
app.post("/upload", upload.single("resume"), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ message: "Please upload a resume file." });
    }

    // Simulated AI processing (Replace with actual logic)
    const optimizedResume = `AI-enhanced resume for ATS compatibility`;

    res.json({ message: "Resume processed successfully!", optimizedResume });
});

// Start Server
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
