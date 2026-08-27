import React from 'react';
import{createRoot}from'react-dom/client';
import App from'./App';
import'./style.css';
import'./institution.css';
import'./equity.css';

createRoot(document.getElementById('root')).render(<App/>);
