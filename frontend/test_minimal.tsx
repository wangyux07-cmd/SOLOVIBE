import React from 'react';

function TestMinimal() {
  console.log("TestMinimal component is being rendered");
  return <div style={{padding: '20px', border: '2px solid red'}}>Minimal Test Component - If you see this, React is working!</div>;
}

export default TestMinimal;