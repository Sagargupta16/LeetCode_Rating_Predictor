import React, { useState, useEffect } from 'react';
import * as tf from '@tensorflow/tfjs';

function PredictionComponent() {
  const [model, setModel] = useState(null);
  const [inputs, setInputs] = useState({
    input1: '',
    input2: '',
    input3: '',
    input4: '',
  });
  const [prediction, setPrediction] = useState('');

  // Load the model
  useEffect(() => {
    tf.loadLayersModel('/model/model.json')
      .then(loadedModel => setModel(loadedModel))
      .catch(e => console.error(e));
  }, []);

  // Handle input change
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setInputs(prevInputs => ({
      ...prevInputs,
      [name]: value,
    }));
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (model) {
      // Assuming input needs to be converted to tensor
      const inputData = tf.tensor([
        parseFloat(inputs.input1),
        parseFloat(inputs.input2),
        parseFloat(inputs.input3),
        parseFloat(inputs.input4),
      ]); // Modify as per your input requirements
      const result = model.predict(inputData);
      result.array().then(array => setPrediction(array[0]));
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input type="text" name="input1" value={inputs.input1} onChange={handleInputChange} />
        <input type="text" name="input2" value={inputs.input2} onChange={handleInputChange} />
        <input type="text" name="input3" value={inputs.input3} onChange={handleInputChange} />
        <input type="text" name="input4" value={inputs.input4} onChange={handleInputChange} />
        <button type="submit">Predict</button>
      </form>
      {prediction && <div>Predicted Rating: {prediction}</div>}
    </div>
  );
}

export default PredictionComponent;
