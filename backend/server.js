require('dotenv').config();
const express  = require('express');
const mongoose = require('mongoose');
const bcrypt   = require('bcryptjs');
const jwt      = require('jsonwebtoken');
const cors     = require('cors');

const app = express();

app.use(express.json());
app.use(cors({
  origin: process.env.FRONTEND_URL || '*',
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

mongoose.connect(process.env.MONGO_URI)
  .then(() => console.log('Connected to MongoDB via Mongoose'))
  .catch(err => console.error('MongoDB Connection Error:', err));

const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true, lowercase: true, trim: true },
  passwordHash: { type: String, required: true },
  name: { type: String, default: '' }
}, { timestamps: true });

const User = mongoose.model('User', userSchema);

function signToken(user) {
  return jwt.sign(
    { email: user.email, name: user.name },
    process.env.JWT_SECRET,
    { expiresIn: '24h' }
  );
}

app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ message: 'Email and password required.' });
  }

  try {
    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) return res.status(401).json({ message: 'Invalid email or password.' });

    const match = await bcrypt.compare(password, user.passwordHash);
    if (!match) return res.status(401).json({ message: 'Invalid email or password.' });

    return res.json({ email: user.email, name: user.name, token: signToken(user) });
  } catch (err) {
    return res.status(500).json({ message: 'Internal Server Error' });
  }
});

app.get('/api/me', async (req, res) => {
  const header = req.headers['authorization'] || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return res.status(401).json({ message: 'No token.' });

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findOne({ email: decoded.email });
    if (!user) return res.status(404).json({ message: 'User not found.' });

    return res.json({
      email: user.email,
      name: user.name,
      token: signToken(user)
    });
  } catch (err) {
    return res.status(401).json({ message: 'Invalid or expired token.' });
  }
});

app.post('/api/register', async (req, res) => {
  const { email, password, name } = req.body;
  if (!email || !password) {
    return res.status(400).json({ message: 'Email and password required.' });
  }

  try {
    const existingUser = await User.findOne({ email: email.toLowerCase() });
    if (existingUser) return res.status(409).json({ message: 'Account already exists.' });

    const passwordHash = await bcrypt.hash(password, 10);
    const newUser = new User({
      email,
      name: name || email,
      passwordHash
    });

    await newUser.save();
    res.json({ message: 'Account created successfully! Log in to access your dashboard.' });
  } catch (err) {
    res.status(500).json({ message: 'Registration failed due to a server error.' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
