import React, { useState, useEffect } from 'react';
import * as tf from '@tensorflow/tfjs';

function PredictionComponent() {
  const [model, setModel] = useState(null);
  const [inputs, setInputs] = useState({
    input1: 0.0,
    input2: 0.0,
    input3: 0.0,
    input4: 0.0,
    input5: 0.0,
  });
  const [scalerValues, setScalerValues] = useState(null);
  const [prediction, setPrediction] = useState('');

  // Load the model
  useEffect(() => {
    tf.loadLayersModel('/model/model.json')
      .then((loadedModel) => setModel(loadedModel))
      .catch((e) => console.error(e));

    // Load scaler values from scaler.save file
    const loadScaler = async () => {
      const scaler = await tf.loadLayersModel('/model/scaler.save');

      // Extract and store scaler values
      const minInput1 = scaler.getLayer('min_input1').getWeights()[0].arraySync();
      const rangeInput1 = scaler.getLayer('range_input1').getWeights()[0].arraySync();
      const minInput2 = scaler.getLayer('min_input2').getWeights()[0].arraySync();
      const rangeInput2 = scaler.getLayer('range_input2').getWeights()[0].arraySync();
      const minInput4 = scaler.getLayer('min_input4').getWeights()[0].arraySync();
      const rangeInput4 = scaler.getLayer('range_input4').getWeights()[0].arraySync();
      const minOutput = scaler.getLayer('min_output').getWeights()[0].arraySync();
      const rangeOutput = scaler.getLayer('range_output').getWeights()[0].arraySync();

      // Save scaler values in state
      setScalerValues({
        minInput1,
        rangeInput1,
        minInput2,
        rangeInput2,
        minInput4,
        rangeInput4,
        minOutput,
        rangeOutput,
      });
    };

    loadScaler();
  }, []);

  // Handle input change
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setInputs((prevInputs) => ({
      ...prevInputs,
      [name]: value,
    }));
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (model && scalerValues) {
      // Normalize inputs using scaler values
      const input1 = (parseFloat(inputs.input1) - scalerValues.minInput1) / scalerValues.rangeInput1;
      const input2 = (parseFloat(inputs.input2) - scalerValues.minInput2) / scalerValues.rangeInput2;
      const input4 = (parseFloat(inputs.input4) - scalerValues.minInput4) / scalerValues.rangeInput4;

      // Apply logic for input3 and input5
      const input3 = input1 / input2;
      const input5 = inputs.input5 === 'Weekly' ? 0 : inputs.input5 === 'Biweekly' ? 1 : -1;

      // Prepare input tensor
      const inputData = tf.tensor([input1, input2, input3, input4, input5]);

      // Predict using the model
      const result = model.predict(inputData);
      result.array().then((array) => setPrediction(array[0]));
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          name="input1"
          value={inputs.input1}
          onChange={handleInputChange}
        />
        <input
          type="text"
          name="input2"
          value={inputs.input2}
          onChange={handleInputChange}
        />
        <input
          type="text"
          name="input3"
          value={inputs.input3}
          readOnly
        />
        <select
          name="input4"
          value={inputs.input4}
          onChange={handleInputChange}
        >
          <option value="0">0</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
        </select>
        <select
          name="input5"
          value={inputs.input5}
          onChange={handleInputChange}
        >
          <option value="Weekly">Weekly</option>
          <option value="Biweekly">Biweekly</option>
          <option value="Other">Other</option>
        </select>
        <button type="submit">Predict</button>
      </form>
      {prediction && <div>Predicted Rating: {prediction}</div>}
    </div>
  );
}

export default PredictionComponent;
