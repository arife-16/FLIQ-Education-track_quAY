import numpy as np
import math
import matplotlib.pyplot as plt
import qiskit
# Qiskit imports
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram, plot_bloch_multivector
from qiskit.providers.basic_provider import BasicSimulator # For statevector

import warnings
warnings.filterwarnings("ignore")

print("Libraries Imported Successfully for Qiskit")

def generate_binary_strings(marked_item_decimal):
    n = int(math.log(marked_item_decimal,2))
    binary_strings = []
    for i in range(2**n):
        binary_string = bin(i)[2:].zfill(n)
        binary_strings.append(binary_string)
    return binary_strings

def make_oracle_qiskit(qc, data_qubits, ancilla_qubit, marked_bitstring):
    """
    Implements the oracle which marks the `marked_bitstring`.
    Args:
        qc (QuantumCircuit): The quantum circuit.
        data_qubits (QuantumRegister or list of Qubit): The data qubits.
        ancilla_qubit (Qubit): The ancilla qubit.
        marked_bitstring: The bitstring to mark in the data qubits.
    """
    # Apply X gates for 0s in marked_bitstring
    for i, bit in enumerate(marked_bitstring):
        if bit == 0:
            qc.x(data_qubits[i])

    # Apply MCX gate
    qc.mcx(data_qubits, ancilla_qubit)

    # Un-apply X gates for 0s
    for i, bit in enumerate(marked_bitstring):
        if bit == 0:
            qc.x(data_qubits[i])

# Qiskit Diffuser (Amplitude Amplification)
def diffuser_qiskit(qc, data_qubits, ancilla_qubit):
    """
    Implements the diffuser (inversion about the mean) operator.
    Args:
        qc (QuantumCircuit): The quantum circuit.
        data_qubits (QuantumRegister or list of Qubit): The data qubits.
        ancilla_qubit_for_mcz_trick (Qubit): Ancilla used to implement MCZ via phase kickback.
                                            Assumes ancilla is in |-> state.
    """
    qc.h(data_qubits)
    qc.x(data_qubits)

    # Implement MCZ using MCX on ancilla in |-> state
    qc.mcx(data_qubits, ancilla_qubit)

    qc.x(data_qubits)
    qc.h(data_qubits)


def grover_circuit_qiskit(n_data_qubits, marked_bitstring, reps=1):
    """
    Constructs the Grover search circuit.
    Args:
        n_data_qubits (int): Number of data qubits.
        marked_bitstring: The bitstring to mark.
        reps (int): Number of Grover iterations.
    Returns:
        QuantumCircuit: The Grover search circuit.
    """
    q_reg = QuantumRegister(n_data_qubits, 'q')
    anc_reg = QuantumRegister(1, 'ancilla') # One ancilla qubit
    c_reg = ClassicalRegister(n_data_qubits, 'c') # For measuring data qubits
    qc = QuantumCircuit(q_reg, anc_reg, c_reg)

    # 1. Initialize data qubits to superposition
    qc.h(q_reg)

    # 2. Initialize ancilla to |-> state (X then H)
    qc.x(anc_reg[0])
    qc.h(anc_reg[0])
    qc.barrier() # For visual separation

    # 3. Apply Grover iterations
    for _ in range(reps):
        # Oracle
        make_oracle_qiskit(qc, q_reg, anc_reg[0], marked_bitstring)
        qc.barrier()
        # Diffuser
        diffuser_qiskit(qc, q_reg, anc_reg[0])
        qc.barrier()

    # 4. Measure data qubits
    qc.measure(q_reg, c_reg)

    return qc

def get_marked_bitstring(marked_item_decimal, nqubits):
    binary_representation = bin(marked_item_decimal)[2:].zfill(nqubits) # Directly get a padded string
    marked_bitstring_list = [eval(i) for i in binary_representation] # Keep the list for the oracle
    return binary_representation, marked_bitstring_list # Return both string and list

def get_reversed_marked_bitstring(marked_bitstring_list):
    return marked_bitstring_list[::-1]

# TESTING FUNCTION
# -----------------------------------------------------------------------------
def run_grover_test(n_data_qubits, marked_item_decimal, num_iterations, shots=1024, success_threshold=0.75):
    """
    Tests the Grover algorithm implementation.

    Args:
        n_data_qubits (int): Number of data qubits for the search.
        marked_item_decimal (int): The decimal value of the item to search for.
        num_iterations (int): Number of Grover iterations to perform.
        shots (int): Number of times to run the simulation.
        success_threshold (float): Minimum probability for the marked item to be considered a success.

    Returns:
        bool: True if the test passes, False otherwise.
        dict: Counts dictionary from the simulation.
    """
    print(f"\n--- Testing Grover for {n_data_qubits} qubits, searching for item '{marked_item_decimal}' with {num_iterations} iterations ---")

    if 2**n_data_qubits <= marked_item_decimal:
        print(f"Error: Marked item {marked_item_decimal} is out of range for {n_data_qubits} qubits (max item is {2**n_data_qubits - 1}).")
        return False, {}
    
    # Get both the string and list representations of the marked bitstring
    marked_bitstring_str, marked_bitstring_list = get_marked_bitstring(marked_item_decimal, n_data_qubits)
    reversed_marked_bitstring = get_reversed_marked_bitstring(marked_bitstring_list) # Use the list for reversal

    circuit = grover_circuit_qiskit(n_data_qubits, reversed_marked_bitstring, reps=num_iterations)

    # Simulate
    simulator = AerSimulator()
    compiled_circuit = transpile(circuit, simulator)
    job = simulator.run(compiled_circuit, shots=shots)
    result = job.result()
    counts = result.get_counts(circuit)
    print(f"Simulation Counts: {counts}")

    # Check for success
    if marked_bitstring_str in counts:
        probability_of_target = counts[marked_bitstring_str] / shots
        print(f"Probability of finding '{marked_bitstring_str}': {probability_of_target:.4f}")
        if probability_of_target >= success_threshold:
            print("Test PASSED: Marked item found with high probability.")
            return True, counts
        else:
            print(f"Test FAILED: Probability ({probability_of_target:.4f}) below threshold ({success_threshold:.2f}).")
            return False, counts
    else:
        print(f"Test FAILED: Marked item '{marked_bitstring_str}' not found in results.")
        return False, counts

# -----------------------------------------------------------------------------
# MAIN EXECUTION BLOCK (Example Tests)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Test Case 1: N=4 (2 qubits), search for "10" (decimal 2), 1 iteration (optimal)
    passed1, _ = run_grover_test(n_data_qubits=2, marked_item_decimal=2, num_iterations=1)
    
    # Test Case 2: N=8 (3 qubits), search for "101" (decimal 5), 2 iterations (near optimal)
    # For N=8, M=1, optimal reps approx pi/4 * sqrt(8) = 2.22 -> 2 reps
    passed2, _ = run_grover_test(n_data_qubits=3, marked_item_decimal=5, num_iterations=2)

    # Test Case 3: N=8 (3 qubits), search for "000" (decimal 0), 2 iterations
    passed3, _ = run_grover_test(n_data_qubits=3, marked_item_decimal=0, num_iterations=2)
    
    # Test Case 4: N=16 (4 qubits), search for "1101" (decimal 13)
    # Optimal reps for N=16, M=1: pi/4 * sqrt(16) = pi -> 3 reps
    passed4, _ = run_grover_test(n_data_qubits=4, marked_item_decimal=13, num_iterations=3)

    print("\n--- Test Summary ---")
    print(f"Test Case 1 (2-qubit, target 2, 1 iter): {'PASSED' if passed1 else 'FAILED'}")
    print(f"Test Case 2 (3-qubit, target 5, 2 iter): {'PASSED' if passed2 else 'FAILED'}")
    print(f"Test Case 3 (3-qubit, target 0, 2 iter): {'PASSED' if passed3 else 'FAILED'}")
    print(f"Test Case 4 (4-qubit, target 13, 3 iter): {'PASSED' if passed4 else 'FAILED'}")


