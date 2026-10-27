
import React from "react";
import {
  Target,
  HeartHandshake,
  TrendingUp,
  Users,
  CheckCircle2,
} from "lucide-react";

import SlideIn from "../SlideIn/SlideIn";
import "./AboutUs.css";

const values = [
  {
    icon: Target,
    title: "Our Mission",
    description:
      "Connect students and early-career workers with meaningful opportunities to gain practical experience and develop valuable skills.",
  },
  {
    icon: HeartHandshake,
    title: "Our Purpose",
    description:
      "Help local businesses, nonprofits, and community organizations find the support they need to make a difference.",
  },
  {
    icon: TrendingUp,
    title: "Our Vision",
    description:
      "Build a community where everyone has the opportunity to learn, contribute, and grow through real-world experiences.",
  },
];

export default function AboutUs() {
  return (
    <section className="grow8-about" id="about">

      
      <SlideIn direction="right" threshold={0.1}>
        <div className="grow8-about-heading">
          <span className="grow8-about-eyebrow">
            GET TO KNOW US
          </span>

          <h2>
            About <span>Grow8</span>
          </h2>

          <p>
            Growing opportunities. Building skills.
            Strengthening communities.
          </p>
        </div>
      </SlideIn>

      
      <SlideIn direction="right" threshold={0.1} delay={200}>
        <div className="grow8-about-intro">
          <div className="grow8-about-intro-content">
            <h3>
              Helping people grow through
              <span> meaningful work.</span>
            </h3>

            <p>
              Grow8 is a platform that brings together students,
              early-career workers, local businesses, nonprofits,
              and event organizers. We make it easier to discover
              short-term opportunities where people can gain
              hands-on experience while supporting their communities.
            </p>

            <ul className="grow8-about-benefits">
              <li>
                <CheckCircle2 size={19} />
                Gain practical experience
              </li>

              <li>
                <CheckCircle2 size={19} />
                Develop real-world skills
              </li>

              <li>
                <CheckCircle2 size={19} />
                Make a positive community impact
              </li>
            </ul>
          </div>

          <div className="grow8-about-visual">
            <div className="grow8-about-visual-circle">
              <Users size={70} strokeWidth={1.5} />
            </div>

            <div className="grow8-about-floating-card">
              <HeartHandshake size={23} />

              <div>
                <strong>Grow Together</strong>
                <span>Learn, contribute, succeed</span>
              </div>
            </div>
          </div>
        </div>
      </SlideIn>

      <div className="grow8-about-values">
        {values.map((value, index) => {
          const Icon = value.icon;

          return (
            <SlideIn
              key={value.title}
              direction="left"
              threshold={0.1}
              delay={index * 100}
            >
              <article className="grow8-about-value-card">
                <div className="grow8-about-value-icon">
                  <Icon size={27} strokeWidth={2} />
                </div>

                <h3>{value.title}</h3>

                <p>{value.description}</p>
              </article>
            </SlideIn>
          );
        })}
      </div>
    </section>
  );
}
