import React from'react';
import{createRoot}from'react-dom/client';
import ProductionApp from'./ProductionApp';
import'./style.css';
import'./institution.css';
import'./equity.css';
import'./production.css';

createRoot(document.getElementById('root')).render(<ProductionApp/>);
