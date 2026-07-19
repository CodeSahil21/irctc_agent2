import { Router } from "express";
import * as authController from "../controllers/auth.controller";
import { authenticate } from "../middleware/authenticate";

const router = Router();

// Public routes
router.post("/register", authController.register);
router.post("/login",    authController.login);
router.post("/refresh",  authController.refresh);

// Protected routes — require valid access token
router.post("/logout",     authenticate, authController.logout);
router.post("/logout-all", authenticate, authController.logoutAll);
router.get("/me",          authenticate, authController.me);

export default router;
