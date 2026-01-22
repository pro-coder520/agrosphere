# Agrosphere API Documentation

## Overview
Agrosphere is a comprehensive agricultural ecosystem platform built with Django REST Framework, featuring AI-powered farming assistance, blockchain integration on Scroll L2, and mobile-first USSD access.

## Authentication
- JWT-based authentication
- Phone number OTP verification

## API Endpoints

### Accounts (`/api/v1/accounts/`)
- `POST /register/` - User registration
- `POST /login/` - User login
- `POST /verify-otp/` - OTP verification
- `GET /profile/` - Get user profile
- `PUT /profile/` - Update profile
- `GET /stats/` - User statistics

### Farming (`/api/v1/farming/`)
- `GET /farms/` - List user's farms
- `POST /farms/` - Create farm
- `GET /farms/{id}/` - Farm details
- `PUT /farms/{id}/` - Update farm
- `DELETE /farms/{id}/` - Delete farm
- `GET /crops/` - List crops
- `POST /crops/` - Create crop
- `GET /crops/{id}/` - Crop details
- `POST /crops/{id}/disease-detection/` - AI disease detection
- `GET /tasks/` - Farm tasks
- `POST /tasks/` - Create task
- `PUT /tasks/{id}/` - Update task
- `POST /voice-assistant/` - AI voice assistant

### Blockchain (`/api/v1/blockchain/`)
- `GET /wallet/balance/` - Get wallet balance
- `POST /wallet/transfer/` - Transfer AgroCoin
- `GET /transactions/` - Transaction history
- `POST /token/purchase/` - Purchase AgroCoin
- `GET /gas-estimate/` - Gas fee estimation

### Marketplace (`/api/v1/marketplace/`)
- `GET /products/` - List products
- `POST /products/` - Create product
- `GET /products/{id}/` - Product details
- `POST /orders/` - Place order
- `GET /orders/` - User's orders
- `POST /products/{id}/reviews/` - Add review

### Investments (`/api/v1/investments/`)
- `GET /opportunities/` - Investment opportunities
- `POST /invest/` - Invest in farm
- `GET /portfolio/` - User's portfolio
- `GET /returns/` - Investment returns

### Experts (`/api/v1/experts/`)
- `GET /experts/` - List experts
- `GET /experts/{id}/` - Expert profile
- `POST /consultations/` - Book consultation
- `GET /consultations/` - User's consultations
- `POST /consultations/{id}/messages/` - Send message

### Notifications (`/api/v1/notifications/`)
- `GET /notifications/` - List notifications
- `PUT /notifications/{id}/read/` - Mark as read
- `PUT /preferences/` - Update preferences

### Analytics (`/api/v1/analytics/`)
- `GET /dashboard/` - Dashboard stats
- `GET /activity/` - User activity logs

### USSD (`/api/v1/ussd/`)
- `POST /callback/` - USSD callback handler

### Health (`/api/v1/health/`)
- `GET /` - System health check

## Deployment
Use Docker Compose for local development:
```bash
docker-compose up --build
```

For production, deploy to cloud with managed Redis/PostgreSQL.

## Blockchain Integration
- Uses Scroll L2 for low-cost, fast transactions (EVM-compatible)
- AgroCoin ERC-20 token deployed on Scroll
- Wallet management with encrypted private keys
- Supports Scroll Sepolia (testnet) and Scroll Mainnet
- Chain IDs: Sepolia=534351, Mainnet=534352
- RPC URLs: https://sepolia-rpc.scroll.io, https://rpc.scroll.io

## AI Features
- Gemini AI for crop recommendations and disease detection
- Voice assistant with speech-to-text (Deepgram) and text-to-speech (YarnGPT)
- Multi-language support (English, Hausa, Yoruba, Igbo, Pidgin)