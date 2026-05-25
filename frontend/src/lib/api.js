import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  timeout: 60000,
});

export const fetchHealth = () => api.get("/health").then((r) => r.data);
export const fetchCategories = () => api.get("/categories").then((r) => r.data.categories);
export const fetchStats = () => api.get("/stats/overview").then((r) => r.data);
export const fetchNodes = (params = {}) =>
  api.get("/graph/nodes", { params }).then((r) => r.data);
export const fetchNode = (id) => api.get(`/graph/nodes/${id}`).then((r) => r.data);
export const fetchRuns = () => api.get("/research/runs").then((r) => r.data.runs);
export const fetchRun = (id) => api.get(`/research/runs/${id}`).then((r) => r.data);
export const fetchActions = (limit = 50) =>
  api.get("/governance/actions", { params: { limit } }).then((r) => r.data.actions);
export const fetchEvents = (params = {}) =>
  api.get("/workflows/events", { params }).then((r) => r.data.events);

export const triggerResearch = (target_domain, query) =>
  api.post("/research/trigger", { target_domain, query }).then((r) => r.data);

export const retrieveSemantic = (query, limit = 10, category) =>
  api.post("/retrieve/semantic", { query, limit, category }).then((r) => r.data);
export const retrieveKeyword = (query, limit = 10, category) =>
  api.post("/retrieve/keyword", { query, limit, category }).then((r) => r.data);
export const retrieveHybrid = (query, limit = 10, category) =>
  api.post("/retrieve/hybrid", { query, limit, category }).then((r) => r.data);
