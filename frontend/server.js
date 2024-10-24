const express = require('express');
const path = require('path');
const app = express();
const axios = require('axios');

// Serve static files
app.use(express.static(path.join(__dirname, 'dist', 'frontend', 'browser')));

// Middleware to parse JSON bodies
app.use(express.json());

// Endpoint to handle embedding API call
app.post('/api/get-embedding', async (req, res) => {
  try {
    const response = await axios.post(
      process.env.EMBEDDING_API_URL,
      req.body,
      {
        headers: {
          'Content-Type': 'application/json',
          'api-key': process.env.EMBEDDING_API_KEY,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error in /api/get-embedding:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Endpoint to handle search API call
app.post('/api/search-documents', async (req, res) => {
  try {
    const response = await axios.post(
      process.env.SEARCH_API_URL,
      req.body,
      {
        headers: {
          'Content-Type': 'application/json',
          'api-key': process.env.SEARCH_API_KEY,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error in /api/search-documents:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Endpoint to handle synthesis API call
app.post('/api/generate-synthesis', async (req, res) => {
  try {
    const fullUrl = `${process.env.GENERATE_API_URL}?code=${process.env.GENERATE_API_KEY}`;
    const response = await axios.post(fullUrl, req.body, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    res.json(response.data);
  } catch (error) {
    console.error('Error in /api/generate-synthesis:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Catch-all handler for Angular routing
app.get('/*', function (req, res) {
  res.sendFile(path.join(__dirname, 'dist', 'frontend', 'browser', 'index.html'));
});

// Start the server
const port = process.env.PORT || 8080;
app.listen(port, () => {
  console.log(`Server is running on port ${port}...`);
});
