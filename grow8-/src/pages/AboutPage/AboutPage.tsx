import { Link } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import AboutUs from "../../components/AboutUs/AboutUs";
import "./PublicInfoPages.css";

export default function AboutPage() {
  return (
    <main className="grow8-info-page">
      <Navbar />
      <div className="grow8-info-content">
        <AboutUs />
        <div className="grow8-info-cta">
          <h2>Ready to grow with us?</h2>
          <p>Find a meaningful opportunity or bring your organization the support it needs.</p>
          <div><Link to="/opportunities">Browse opportunities</Link><Link to="/login?mode=signup">Get started</Link></div>
        </div>
      </div>
    </main>
  );
}
