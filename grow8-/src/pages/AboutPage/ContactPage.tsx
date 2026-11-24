import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { MessageCircle, Search, Users } from "lucide-react";
import Navbar from "../../components/Navbar/Navbar";
import "./PublicInfoPages.css";

export default function ContactPage() {
  const [sent, setSent] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSent(true);
  }

  return (
    <main className="grow8-info-page">
      <Navbar />
      <div className="grow8-contact-content">
        <header className="grow8-contact-heading">
          <span>WE’RE HERE TO HELP</span>
          <h1>Contact Grow8</h1>
          <p>Have a question about opportunities, applications, or your organization? Send us a message.</p>
        </header>
        <div className="grow8-contact-grid">
          <form className="grow8-contact-form" onSubmit={submit}>
            <label>Your name<input name="name" required autoComplete="name" /></label>
            <label>Email address<input name="email" type="email" required autoComplete="email" /></label>
            <label>I'm contacting as
              <select name="role" defaultValue="contributor">
                <option value="contributor">Contributor</option>
                <option value="creator">Organization / Creator</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>Message<textarea name="message" rows={6} required maxLength={3000} /></label>
            {sent && <p className="grow8-contact-success" role="status">Thanks for reaching out. Your message is ready for the Grow8 team.</p>}
            <button type="submit"><MessageCircle size={17} /> Send message</button>
          </form>
          <aside className="grow8-contact-help">
            <h2>Looking for something?</h2>
            <Link to="/opportunities"><Search size={18} /><span><strong>Find opportunities</strong><small>Browse current openings and application details.</small></span></Link>
            <Link to="/login?mode=signup"><Users size={18} /><span><strong>Join Grow8</strong><small>Create an account to apply or post opportunities.</small></span></Link>
          </aside>
        </div>
      </div>
    </main>
  );
}
