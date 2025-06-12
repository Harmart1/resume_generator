const mongoose = require("mongoose");

// Connect to MongoDB
mongoose.connect("mongodb://localhost:27017/revisumeDB", {
    useNewUrlParser: true,
    useUnifiedTopology: true
});

// Define Resume Schema
const resumeSchema = new mongoose.Schema({
    filename: String,
    content: String,
    optimizedVersion: String,
    dateUploaded: { type: Date, default: Date.now }
});

const Resume = mongoose.model("Resume", resumeSchema);

// Save Resume to Database
async function saveResume(filename, content, optimizedVersion) {
    const newResume = new Resume({ filename, content, optimizedVersion });
    await newResume.save();
    console.log("Resume saved successfully!");
}

// Export Database Functions
module.exports = { saveResume };
