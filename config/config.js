require("dotenv").config();

const config = {
    PORT: process.env.PORT || 3000,
    DATABASE_URL: process.env.DATABASE_URL || "mongodb://localhost:27017/revisumeDB",
    AI_API_KEY: process.env.AI_API_KEY || "your-ai-api-key-here"
};

module.exports = config;
