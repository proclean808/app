import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import VentureFerretConsole from "@/components/VentureFerretConsole";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<VentureFerretConsole />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
