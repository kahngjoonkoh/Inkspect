export default function Disclaimer() {
  return (
    <div className="notice" role="note">
      <strong>Not a clinical diagnosis.</strong> Inkspect is an experimental, automated take on the Rorschach test.
      Its scoring is machine-generated and unreviewed, and its results must not be used to diagnose, treat or make
      decisions about anyone. If you are worried about your mental health, please talk to a qualified professional
      or{' '}
      <a href="https://findahelpline.com" target="_blank" rel="noreferrer">
        find a free helpline near you
      </a>
      .
    </div>
  )
}
