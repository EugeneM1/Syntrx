import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Analytics } from "@vercel/analytics/react";
import App from "./App";
import Home from "./pages/Home";
import Report from "./pages/Report";
import Interactions from "./pages/Interactions";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import { AuthProvider } from "./lib/auth";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<App />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/report/:id" element={<Report />} />
            <Route path="/interactions/:id" element={<Interactions />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Analytics />
    </AuthProvider>
  </React.StrictMode>,
);
