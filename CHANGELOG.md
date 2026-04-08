# Changelog

All notable changes to the StockPilot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-15

### Added

#### Authentication & Authorization
- Session-based authentication with secure cookie handling
- User registration with email validation and password hashing via bcrypt
- User login and logout endpoints
- Protected routes requiring active session
- Role-based access control (RBAC) with `admin` and `user` roles
- Permission guards on API endpoints based on user role

#### Inventory Management
- Full CRUD operations for inventory items (create, read, update, delete)
- Ownership-based access control — users can only manage their own inventory items
- Admin override to view and manage all inventory items across users
- Inventory item fields: name, description, quantity, price, SKU, category, status
- Low stock threshold alerts for inventory items

#### Category Management
- CRUD operations for item categories
- Hierarchical category support
- Category assignment to inventory items
- Admin-only category creation and deletion

#### Admin Dashboard
- Aggregated inventory statistics (total items, total value, low stock count)
- User activity overview
- System-wide inventory summary by category
- Admin-only access enforcement

#### User Management
- Admin endpoints for listing, viewing, and managing user accounts
- Role assignment and modification by admin users
- User profile viewing and editing for authenticated users
- Account deactivation support

#### Search, Filter & Sort
- Full-text search across inventory item names and descriptions
- Filter inventory by category, status, and stock level
- Sort inventory by name, quantity, price, or date created
- Paginated API responses with configurable page size

#### Responsive UI
- Jinja2-based server-rendered templates
- Tailwind CSS utility-first responsive design
- Mobile-friendly navigation and layout
- Dashboard with responsive grid and card components
- Form components for inventory and category management

#### Deployment & Infrastructure
- Vercel deployment configuration and support
- Environment-based configuration via Pydantic Settings and `.env` files
- SQLAlchemy 2.0 async database layer with SQLite support
- Alembic database migration setup
- Structured logging throughout the application
- CORS middleware configuration for production and development environments